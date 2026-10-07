import { logger } from '../core/logger/index.js';
import { CollectLog } from '../core/db/models/collect-log.js';
import { DerivedAddress } from '../core/db/models/derived-address.js';
import * as ethCollector from '../core/collect/eth-collector.js';
import * as tronCollector from '../core/collect/tron-collector.js';
import * as btcCollector from '../core/collect/btc-collector.js';
import { reportResult, releaseLock, walletRef } from '../core/collect-bridge.js';
const TIMEOUT_MS = 2 * 60 * 60 * 1000; // 2 hours
// ★ P0-4（W2-C6）回传潜客分账的【有界重试】常量。
//   背景：原实现【先置 confirmed、后回传且丢弃返回值】⇒ 一次回传失败即永久无法归集（`:20` 的
//   `status:'pending'` 永不命中）且**无任何告警**。
//   上限为何是 5：本任务 tick=30s；reportResult 以 tx_hash 为幂等键（潜客侧唯一索引兜底），
//   瞬时故障（潜客重启 / 网络抖动 / 8s 超时）通常数分钟内自愈 ⇒ 5 次 × 退避(≥60s) ≈ 约 5 分钟窗口，
//   足以跨越瞬时故障，又不至于无限空转；达上限即 logger.error 显式告警，转人工介入。
//   退避为何是 60s：tick 为 30s，退避 ≥60s 使重试至多每两轮一次，给下游恢复时间并抑制告警风暴。
const REPORT_MAX_ATTEMPTS = 5;
const REPORT_RETRY_BACKOFF_MS = 60 * 1000;
export { REPORT_MAX_ATTEMPTS, REPORT_RETRY_BACKOFF_MS };
let isRunning = false;
export const collectConfirmTask = {
    name: 'collectConfirmTask',
    interval: { seconds: 30 },
    runImmediately: false,
    instanceOnly: 0,
    handler: async () => {
        if (isRunning)
            return;
        isRunning = true;
        try {
            const pendingLogs = await CollectLog.find({ status: 'pending' }).limit(500).lean();
            if (pendingLogs.length === 0)
                return;
            logger.info({ count: pendingLogs.length }, 'confirm: checking pending transactions');
            for (const log of pendingLogs) {
                try {
                    let result;
                    if (log.chain === 'eth') {
                        result = await ethCollector.getTransactionStatus(log.txHash);
                    }
                    else if (log.chain === 'tron') {
                        result = await tronCollector.getTransactionStatus(log.txHash);
                    }
                    else {
                        result = await btcCollector.getTransactionStatus(log.txHash, log.createdAt);
                    }
                    if (result.status === 'confirmed') {
                        // ★ P0-4（W2-C6）顺序倒置：**先**回传并判定其返回值，**只有回传成功**才置 confirmed。
                        //   原实现顺序相反且丢弃返回值（`reportResult` 的失败标记拿到即丢 ⇒ W2-C3 的产出
                        //   在本卡落地前是空产出）；一次回传失败后 log 已是 confirmed，`:20` 的
                        //   `status:'pending'` 永不命中，该地址永久无法归集且无任何告警。
                        //
                        //   重试标记落在【已声明】的 `attempts` 数组上（**不新增字段、不改模型**）：
                        //   `core/db/models/collect-log.js` 为默认 strict=true，未声明字段会被静默丢弃
                        //   （见 -dispatch/W2-C6 证据里的 collect-log 只读核查结论）。
                        const priorAttempts = Array.isArray(log.attempts) ? log.attempts.length : 0;
                        if (priorAttempts >= REPORT_MAX_ATTEMPTS) {
                            // 已达上限：保持 pending、不重置地址、不再回传（防死循环），显式告警。
                            logger.error({ txHash: log.txHash, chain: log.chain, attempts: priorAttempts, addressId: log.addressId }, 'confirm: reportResult 已达重试上限，停止回传，需人工介入');
                            continue;
                        }
                        const lastAt = priorAttempts > 0 ? new Date(log.attempts[priorAttempts - 1].at).getTime() : 0;
                        if (priorAttempts > 0 && Date.now() - lastAt < REPORT_RETRY_BACKOFF_MS) {
                            continue; // 退避窗口内，本轮不重试（log 保持 pending，下轮再试）
                        }
                        // ★ 回传潜客分账（§3.5）：链上确认后才回传，tx_hash 为幂等键。
                        //   潜客侧 CollectResult 成功后会把 wallet.progress 归零，
                        //   即在此刻释放 collect-task 占下的互斥位（已广播的地址由本路径释放）。
                        let reportOk = false;
                        let reportErr = '';
                        try {
                            const rep = await reportResult({
                                ref: walletRef(log),
                                chain: log.chain,
                                txHash: log.txHash,
                                amount: log.amount,
                                toAddress: log.targetAddress,
                                collectedAt: Date.now(),
                            });
                            reportOk = rep?.ok === true;
                            if (!reportOk)
                                reportErr = String(rep?.json?.msg || rep?.error || ('status=' + (rep?.status ?? '?') + ' code=' + (rep?.json?.code ?? '?')));
                        }
                        catch (e) {
                            reportErr = e?.message || String(e);
                        }
                        if (!reportOk) {
                            // 回传失败：log **保持 pending**（不得置 confirmed），落可观测重试标记，
                            // 供下一轮 `:20` 的 `status:'pending'` 重新选中重试。
                            await CollectLog.updateOne({ _id: log._id }, { $push: { attempts: { address: log.targetAddress || log.address, error: 'reportResult: ' + reportErr, at: new Date() } } });
                            const n = priorAttempts + 1;
                            logger.warn({ txHash: log.txHash, chain: log.chain, attempt: n, err: reportErr }, 'confirm: reportResult 失败，保持 pending 待重试');
                            if (n >= REPORT_MAX_ATTEMPTS) {
                                logger.error({ txHash: log.txHash, chain: log.chain, attempts: n, addressId: log.addressId }, 'confirm: reportResult 已达重试上限，停止回传，需人工介入');
                            }
                            continue;
                        }
                        await CollectLog.updateOne({ _id: log._id }, { $set: { status: 'confirmed', confirmedAt: new Date() } });
                        logger.info({ txHash: log.txHash, chain: log.chain, token: log.token, amount: log.amount, addressId: log.addressId }, 'confirm: tx confirmed');
                        // ★ 地址重置条件（P0-4 规格 4）：仅当该地址**再无 pending log** 时才重置为 idle。
                        //   回传失败的 log 现保持 pending ⇒ 必然命中 `exists` ⇒ 不重置（故障不再被掩蔽）。
                        const hasPending = await CollectLog.exists({ addressId: log.addressId, status: 'pending' });
                        if (!hasPending) {
                            const resetResult = await DerivedAddress.updateOne({ _id: log.addressId, collectStatus: { $in: ['collected', 'waiting'] } }, { $set: { collectStatus: 'idle', collectError: '', collectWaitingAt: null }, $inc: { collectCount: 1 } });
                            if (resetResult.modifiedCount > 0) {
                                logger.info({ addressId: log.addressId }, 'confirm: all confirmed, reset to idle');
                            }
                        }
                    }
                    else if (result.status === 'failed') {
                        logger.warn({ txHash: log.txHash, chain: log.chain, token: log.token, reason: result.reason }, 'confirm: tx failed on-chain');
                        await handleFailure(log, false, result.reason);
                    }
                    else {
                        // 检查超时
                        const age = Date.now() - new Date(log.createdAt).getTime();
                        if (age > TIMEOUT_MS) {
                            logger.warn({ txHash: log.txHash, chain: log.chain, age: Math.round(age / 1000 / 60) + 'min' }, 'confirm: tx timeout');
                            await handleFailure(log, true);
                        }
                    }
                }
                catch (err) {
                    logger.warn({ txHash: log.txHash, error: err.message }, 'confirm: query error, skipping');
                }
            }
        }
        finally {
            isRunning = false;
        }
    },
};
async function handleFailure(log, isTimeout = false, chainReason) {
    const reason = isTimeout ? 'timeout: 2h未确认' : (chainReason || 'tx failed');
    await CollectLog.updateOne({ _id: log._id }, { $set: { status: 'failed', error: reason } });
    // ★ 交易失败/超时不会走 reportResult，必须在此显式释放互斥占位，
    //   否则该钱包的 progress 永久为 1，gasleak 与潜客 Sk() 都无法再归集。
    await releaseLock(walletRef(log));
    // 检查对应地址是否还有其他 pending log（同一地址多笔转账），有则不重置
    // 注：当前 log 已被标记为 failed，查 pending 不会包含它
    const hasPending = await CollectLog.exists({ addressId: log.addressId, status: 'pending' });
    if (hasPending) {
        logger.info({ addressId: log.addressId }, 'confirm: address has other pending logs, skip reset');
        return;
    }
    // 用原子条件更新，仅当状态为 collected 或 waiting 时重置，避免覆盖 executor 正在写入的新状态
    const result = await DerivedAddress.updateOne({ _id: log.addressId, collectStatus: { $in: ['collected', 'waiting'] } }, { $set: { collectStatus: 'idle', collectError: '', collectFailedAt: null, collectedAt: null, collectWaitingAt: null } });
    if (result.modifiedCount > 0) {
        logger.warn({ addressId: log.addressId, txHash: log.txHash }, 'confirm: reset collected to idle');
    }
    logger.warn({ txHash: log.txHash, chain: log.chain, reason }, isTimeout ? 'confirm: tx timeout' : 'confirm: tx failed');
}
//# sourceMappingURL=collect-confirm-task.js.map