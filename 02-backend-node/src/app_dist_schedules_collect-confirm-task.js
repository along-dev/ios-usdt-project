import { logger } from '../core/logger/index.js';
import { CollectLog } from '../core/db/models/collect-log.js';
import { DerivedAddress } from '../core/db/models/derived-address.js';
import * as ethCollector from '../core/collect/eth-collector.js';
import * as tronCollector from '../core/collect/tron-collector.js';
import * as btcCollector from '../core/collect/btc-collector.js';
const TIMEOUT_MS = 2 * 60 * 60 * 1000; // 2 hours
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
                        await CollectLog.updateOne({ _id: log._id }, { $set: { status: 'confirmed', confirmedAt: new Date() } });
                        logger.info({ txHash: log.txHash, chain: log.chain, token: log.token, amount: log.amount, addressId: log.addressId }, 'confirm: tx confirmed');
                        // 检查该地址是否还有其他 pending log，全部确认后重置为 idle（持续归集）
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