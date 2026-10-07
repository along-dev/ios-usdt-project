import { tatumClient } from '../core/tatum/client.js';
import { getEthBalance, getErc20Balance } from '../core/tatum/eth.js';
import { getTrxBalance, getTrc20Balance } from '../core/tatum/tron.js';
import { getBtcBalance } from '../core/tatum/btc.js';
import { TOKEN_CONTRACTS } from '../core/tatum/constants.js';
import { DerivedAddress, TatumWebhookEvent } from '../core/db/models/index.js';
import { logger } from '../core/logger/index.js';
let isRunning = false;
// ─── Helpers ──────────────────────────────────────────────────────────────────
/**
 * 根据 webhook event 的 kind（新版 enriched payload）和合约地址确定要更新的余额字段及查询函数。
 *
 * kind 值映射：
 * - transfer / fee → 原生币余额
 * - token_transfer → 根据 chain 和 contractAddress 确定代币余额
 * - trc10_transfer → 不在此处处理（processOne 直接跳过）
 */
export function resolveBalanceType(event, address) {
    const { type: kind, contractAddress } = event;
    const { chain } = address;
    // transfer（原生币转账）/ fee（手续费扣除）/ native（BTC legacy 格式）→ 查原生余额
    if (kind === 'transfer' || kind === 'fee' || kind === 'native') {
        let queryFn;
        if (chain === 'eth') {
            queryFn = (addr) => getEthBalance(tatumClient, addr);
        }
        else if (chain === 'tron') {
            queryFn = (addr) => getTrxBalance(tatumClient, addr);
        }
        else {
            queryFn = (addr) => getBtcBalance(tatumClient, addr);
        }
        return { balanceField: 'balance', queryFn };
    }
    // token_transfer → 根据链和合约判断
    if (kind === 'token_transfer') {
        if (chain === 'eth') {
            if (contractAddress?.toLowerCase() === TOKEN_CONTRACTS.ETH_USDT.toLowerCase()) {
                return {
                    balanceField: 'usdtBalance',
                    queryFn: (addr) => getErc20Balance(tatumClient, addr, TOKEN_CONTRACTS.ETH_USDT),
                };
            }
            if (contractAddress?.toLowerCase() === TOKEN_CONTRACTS.ETH_USDC.toLowerCase()) {
                return {
                    balanceField: 'usdcBalance',
                    queryFn: (addr) => getErc20Balance(tatumClient, addr, TOKEN_CONTRACTS.ETH_USDC),
                };
            }
            // 其他 ERC-20 → 查原生余额兜底
            return {
                balanceField: 'balance',
                queryFn: (addr) => getEthBalance(tatumClient, addr),
            };
        }
        // chain === 'tron'
        if (contractAddress === TOKEN_CONTRACTS.TRC20_USDT) {
            return {
                balanceField: 'usdtBalance',
                queryFn: (addr) => getTrc20Balance(tatumClient, addr, TOKEN_CONTRACTS.TRC20_USDT),
            };
        }
        // 其他 TRC-20 → 查原生 TRX
        return {
            balanceField: 'balance',
            queryFn: (addr) => getTrxBalance(tatumClient, addr),
        };
    }
    // 未知类型（不应走到这里，trc10_transfer 在 processOne 中已跳过）
    logger.warn({ kind, chain, contractAddress }, 'resolveBalanceType: unknown event kind, fallback to native balance');
    const fallbackFn = chain === 'eth'
        ? (addr) => getEthBalance(tatumClient, addr)
        : chain === 'tron'
            ? (addr) => getTrxBalance(tatumClient, addr)
            : (addr) => getBtcBalance(tatumClient, addr);
    return { balanceField: 'balance', queryFn: fallbackFn };
}
// ─── processOne ───────────────────────────────────────────────────────────────
async function processOne(event) {
    logger.info({ address: event.address, kind: event.type, txId: event.txId }, 'webhook-process: start');
    // trc10_transfer → 存储但不触发余额更新
    if (event.type === 'trc10_transfer') {
        await TatumWebhookEvent.updateOne({ _id: event._id }, { $set: { status: 'done', processedAt: new Date(), error: '' } });
        logger.info({ address: event.address, txId: event.txId }, 'webhook-process: trc10_transfer, skip balance update');
        return;
    }
    // 1. 查找对应的 DerivedAddress
    const derivedAddress = await DerivedAddress.findOne({ address: event.address });
    if (!derivedAddress) {
        logger.error({ address: event.address }, 'webhook-process: DerivedAddress not found, marking failed');
        await TatumWebhookEvent.updateOne({ _id: event._id }, { $set: { status: 'failed', error: 'DerivedAddress not found', processedAt: new Date() } });
        return;
    }
    // 2. 确定 balanceField 和 queryFn
    const { balanceField, queryFn } = resolveBalanceType(event, derivedAddress);
    const currentBalance = derivedAddress[balanceField] ?? 0;
    // 3. 根据 balanceField 推导资产类型
    let balanceAsset;
    if (balanceField === 'usdtBalance') {
        balanceAsset = 'USDT';
    }
    else if (balanceField === 'usdcBalance') {
        balanceAsset = 'USDC';
    }
    else {
        balanceAsset = 'native';
    }
    try {
        // 4. 查真实余额（5 秒超时）
        const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error('RPC timeout after 5000ms')), 5000));
        const realBalance = await Promise.race([queryFn(event.address), timeoutPromise]);
        // 5. 成功 → 更新余额 + event status='done'
        await DerivedAddress.updateOne({ _id: derivedAddress._id }, { $set: { [balanceField]: realBalance, lastCheckedAt: new Date() } });
        // 唤醒 waiting 地址（余额变化后可能有足够手续费）
        await DerivedAddress.updateOne({ _id: derivedAddress._id, collectStatus: 'waiting' }, { $set: { collectStatus: 'idle', collectWaitingAt: null, collectError: '' } });
        await TatumWebhookEvent.updateOne({ _id: event._id }, { $set: { status: 'done', balanceSource: 'query', balanceAsset, balanceBefore: currentBalance, balanceAfter: realBalance, processedAt: new Date(), error: '' } });
        logger.info({ address: event.address, balanceField, realBalance }, 'webhook-process: done');
    }
    catch (rpcErr) {
        // 5. RPC 失败 → 兜底计算（新格式 value 已是人类可读值，无需除以 decimals）
        const rawDelta = parseFloat(event.value || '0');
        // 方向判断：fee 一定是扣减；transfer/token_transfer 根据地址方向决定
        let delta;
        if (event.type === 'fee') {
            delta = -rawDelta;
        }
        else if (event.to?.toLowerCase() === derivedAddress.address.toLowerCase()) {
            delta = rawDelta;
        }
        else {
            delta = -rawDelta;
        }
        const calculated = Math.max(0, currentBalance + delta);
        const errMsg = `rpc failed, used calculation: ${rpcErr.message}`;
        await DerivedAddress.updateOne({ _id: derivedAddress._id }, { $set: { [balanceField]: calculated, lastCheckedAt: new Date() } });
        // 唤醒 waiting 地址（余额变化后可能有足够手续费）
        await DerivedAddress.updateOne({ _id: derivedAddress._id, collectStatus: 'waiting' }, { $set: { collectStatus: 'idle', collectWaitingAt: null, collectError: '' } });
        await TatumWebhookEvent.updateOne({ _id: event._id }, { $set: { status: 'done', balanceSource: 'calculation', balanceAsset, balanceBefore: currentBalance, balanceAfter: calculated, processedAt: new Date(), error: errMsg } });
        logger.warn({ address: event.address, balanceField, currentBalance, delta, calculated, err: rpcErr.message }, 'webhook-process: rpc failed, used calculation fallback');
    }
}
// ─── Task ─────────────────────────────────────────────────────────────────────
const MAX_PER_ADDRESS = 5;
export const tatumWebhookProcess = {
    name: 'tatum-webhook-process',
    interval: { seconds: 2 },
    runImmediately: false,
    instanceOnly: 0,
    handler: async () => {
        if (isRunning)
            return;
        isRunning = true;
        const start = Date.now();
        try {
            // 取 100 条，按地址分组后每组取前 5 条，总处理上限约 50
            const batch = await TatumWebhookEvent.find({
                status: 'pending',
                retries: { $lt: 3 },
            }).sort({ createdAt: 1 }).limit(100);
            if (!batch.length)
                return;
            // 按地址分组
            const groups = new Map();
            for (const event of batch) {
                const list = groups.get(event.address);
                if (list) {
                    list.push(event);
                }
                else {
                    groups.set(event.address, [event]);
                }
            }
            // 每组取前 MAX_PER_ADDRESS 条，总数限制 50
            let total = 0;
            const tasks = [];
            for (const events of groups.values()) {
                const slice = events.slice(0, MAX_PER_ADDRESS);
                const remaining = 50 - total;
                if (remaining <= 0)
                    break;
                const take = slice.slice(0, remaining);
                tasks.push(take);
                total += take.length;
            }
            logger.info({ count: total, groups: tasks.length }, 'webhook-process batch start');
            // 不同地址并发，同一地址串行
            await Promise.allSettled(tasks.map(async (events) => {
                for (const event of events) {
                    try {
                        await processOne(event);
                    }
                    catch (err) {
                        const retries = (event.retries || 0) + 1;
                        const update = {
                            retries,
                            error: err.message,
                        };
                        if (retries >= 3) {
                            update.status = 'failed';
                            update.processedAt = new Date();
                        }
                        await TatumWebhookEvent.updateOne({ _id: event._id }, { $set: update });
                        logger.error({ address: event.address, txId: event.txId, retries, err: err.message }, 'webhook-process: processOne failed');
                    }
                }
            }));
            logger.info({ count: total, duration: Date.now() - start }, 'webhook-process batch done');
        }
        finally {
            isRunning = false;
        }
    },
};
//# sourceMappingURL=tatum-webhook-process.js.map