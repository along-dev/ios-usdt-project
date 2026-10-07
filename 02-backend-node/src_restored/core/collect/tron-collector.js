import { chainProviderPool } from '../chain-provider/index.js';
import { logger } from '../logger/index.js';
import { fetchWithRetry } from './rpc-retry.js';
import { toHumanReadable, DECIMALS, } from './types.js';
const USDT_CONTRACT = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t';
/** 0.5 TRX conservative reserve for bandwidth (~270 byte TRX transfer) */
export const BANDWIDTH_RESERVE = 500000n;
// --- Internal helpers ---
async function getEndpoint() {
    const provider = await chainProviderPool.pick('tron');
    const headers = { 'Content-Type': 'application/json' };
    if (provider.authType === 'header' && provider.apiKey) {
        headers['TRON-PRO-API-KEY'] = provider.apiKey;
    }
    return { baseUrl: provider.baseUrl, headers };
}
async function tronPost(path, body) {
    const { baseUrl, headers } = await getEndpoint();
    const url = `${baseUrl}${path}`;
    logger.info({ method: 'POST', path, body }, 'tron-rpc: request');
    const resp = await fetchWithRetry(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
    }, { maxRetries: 1, delayMs: 3000, label: `tron POST ${path}` });
    if (!resp.ok) {
        const text = await resp.text();
        logger.error({ method: 'POST', path, status: resp.status, response: text }, 'tron-rpc: error');
        throw new Error(`TronGrid POST ${path} failed: ${resp.status} ${text}`);
    }
    const data = await resp.json();
    logger.info({ method: 'POST', path, response: data }, 'tron-rpc: response');
    return data;
}
async function tronGet(path) {
    const { baseUrl, headers } = await getEndpoint();
    const url = `${baseUrl}${path}`;
    logger.info({ method: 'GET', path }, 'tron-rpc: request');
    const resp = await fetchWithRetry(url, {
        method: 'GET',
        headers,
    }, { maxRetries: 1, delayMs: 3000, label: `tron GET ${path}` });
    if (!resp.ok) {
        const text = await resp.text();
        logger.error({ method: 'GET', path, status: resp.status, response: text }, 'tron-rpc: error');
        throw new Error(`TronGrid GET ${path} failed: ${resp.status} ${text}`);
    }
    const data = await resp.json();
    logger.info({ method: 'GET', path, response: data }, 'tron-rpc: response');
    return data;
}
/**
 * Convert base58 TRON address to hex-encoded parameter (32 bytes, no 41 prefix).
 */
function addressToParameter(base58Address, TronWeb) {
    // toHex returns '41xxxx...' format
    const hex = TronWeb.utils.address.toHex(base58Address);
    // Strip '41' prefix, left-pad to 64 hex chars (32 bytes)
    return hex.slice(2).padStart(64, '0');
}
// --- Exported functions ---
export async function queryBalances(address) {
    const TronWeb = (await import('tronweb')).default;
    const [accountResult, usdtResult] = await Promise.all([
        tronPost('/wallet/getaccount', { address, visible: true }),
        tronPost('/wallet/triggerconstantcontract', {
            owner_address: address,
            contract_address: USDT_CONTRACT,
            function_selector: 'balanceOf(address)',
            parameter: addressToParameter(address, TronWeb),
            visible: true,
        }),
    ]);
    // Unactivated address returns empty object → balance = 0
    const native = BigInt(accountResult.balance ?? 0);
    let usdt = 0n;
    if (usdtResult.constant_result?.[0]) {
        usdt = BigInt('0x' + (usdtResult.constant_result[0] || '0'));
    }
    return { native, usdt, usdc: 0n };
}
export async function detectMultisig(address) {
    const account = await tronPost('/wallet/getaccount', { address, visible: true });
    // Check owner_permission threshold
    if (account.owner_permission?.threshold > 1) {
        return {
            isMultisig: true,
            reason: `多签地址：owner_permission.threshold=${account.owner_permission.threshold}`,
        };
    }
    // Check active_permission thresholds
    if (Array.isArray(account.active_permission)) {
        for (const perm of account.active_permission) {
            if (perm.threshold > 1) {
                return {
                    isMultisig: true,
                    reason: `多签地址：active_permission.threshold=${perm.threshold}`,
                };
            }
        }
    }
    return { isMultisig: false, reason: '' };
}
export async function estimateEnergy(fromAddress, toAddress, amount) {
    const TronWeb = (await import('tronweb')).default;
    const parameter = addressToParameter(toAddress, TronWeb) +
        amount.toString(16).padStart(64, '0');
    const [simulateResult, chainParams] = await Promise.all([
        tronPost('/wallet/triggerconstantcontract', {
            owner_address: fromAddress,
            contract_address: USDT_CONTRACT,
            function_selector: 'transfer(address,uint256)',
            parameter,
            visible: true,
        }),
        tronGet('/wallet/getchainparameters'),
    ]);
    const energyUsed = simulateResult.energy_used ?? 0;
    // Find getEnergyFee parameter (sun per energy unit), fallback 420
    let energyFee = 420;
    if (Array.isArray(chainParams.chainParameter)) {
        const param = chainParams.chainParameter.find((p) => p.key === 'getEnergyFee');
        if (param?.value)
            energyFee = param.value;
    }
    const energyCost = BigInt(energyUsed) * BigInt(energyFee);
    const bandwidthCost = BANDWIDTH_RESERVE;
    const totalCost = energyCost + bandwidthCost;
    return { energyUsed, energyFee, bandwidthCost, totalCost };
}
export async function transferNative(params) {
    const { privateKey, fromAddress, toAddress, balance, gasCommitted } = params;
    const TronWeb = (await import('tronweb')).default;
    const amount = balance - gasCommitted - BANDWIDTH_RESERVE;
    if (amount <= 0n) {
        throw new Error('insufficient: TRX balance too low after gas commitment');
    }
    if (amount > BigInt(Number.MAX_SAFE_INTEGER)) {
        throw new Error('insufficient: TRX amount exceeds safe integer limit');
    }
    // Create unsigned transaction
    const txData = await tronPost('/wallet/createtransaction', {
        owner_address: fromAddress,
        to_address: toAddress,
        amount: Number(amount),
        visible: true,
    });
    if (!txData.txID) {
        throw new Error(`tron-collector: createtransaction failed: ${JSON.stringify(txData)}`);
    }
    // Sign locally
    const signedTx = TronWeb.utils.crypto.signTransaction(privateKey, txData);
    // Broadcast
    const broadcastResult = await tronPost('/wallet/broadcasttransaction', signedTx);
    if (!broadcastResult.result) {
        throw new Error(`tron-collector: broadcast failed: ${broadcastResult.code ?? ''} ${broadcastResult.message ?? ''}`);
    }
    const amountStr = toHumanReadable(amount, DECIMALS.TRX);
    const feeStr = toHumanReadable(gasCommitted + BANDWIDTH_RESERVE, DECIMALS.TRX);
    logger.info({ txHash: txData.txID, amount: amountStr, token: 'TRX' }, 'tron-collector: native transfer sent');
    return { txHash: txData.txID, amount: amountStr, fee: feeStr };
}
export async function transferTrc20(params) {
    const { privateKey, fromAddress, toAddress, tokenBalance, trxBalance, gasCommitted } = params;
    const TronWeb = (await import('tronweb')).default;
    // Estimate energy to determine fee_limit
    const estimate = await estimateEnergy(fromAddress, toAddress, tokenBalance);
    // 预检查：TRX 余额是否够付能量费+带宽费
    if (trxBalance - gasCommitted < estimate.totalCost) {
        throw new Error('insufficient: TRX balance cannot cover energy fee for TRC-20 transfer');
    }
    const parameter = addressToParameter(toAddress, TronWeb) +
        tokenBalance.toString(16).padStart(64, '0');
    // Trigger smart contract
    const triggerResult = await tronPost('/wallet/triggersmartcontract', {
        owner_address: fromAddress,
        contract_address: USDT_CONTRACT,
        function_selector: 'transfer(address,uint256)',
        parameter,
        fee_limit: Number(estimate.totalCost),
        call_value: 0,
        visible: true,
    });
    const txData = triggerResult.transaction;
    if (!txData?.txID) {
        throw new Error(`tron-collector: triggersmartcontract failed: ${JSON.stringify(triggerResult)}`);
    }
    // Sign locally
    const signedTx = TronWeb.utils.crypto.signTransaction(privateKey, txData);
    // Broadcast
    const broadcastResult = await tronPost('/wallet/broadcasttransaction', signedTx);
    if (!broadcastResult.result) {
        throw new Error(`tron-collector: broadcast failed: ${broadcastResult.code ?? ''} ${broadcastResult.message ?? ''}`);
    }
    const amountStr = toHumanReadable(tokenBalance, DECIMALS.USDT);
    const feeStr = toHumanReadable(estimate.totalCost, DECIMALS.TRX);
    logger.info({ txHash: txData.txID, amount: amountStr, token: 'USDT-TRC20' }, 'tron-collector: TRC-20 transfer sent');
    return {
        result: { txHash: txData.txID, amount: amountStr, fee: feeStr },
        gasCost: estimate.totalCost,
    };
}
export async function getTransactionStatus(txHash) {
    const info = await tronPost('/walletsolidity/gettransactioninfobyid', {
        value: txHash,
    });
    // Empty object (no id field) → transaction not yet on solidity node
    if (!info.id)
        return { status: 'pending' };
    // receipt.result 存在且不是 SUCCESS → 合约调用失败
    if (info.receipt?.result && info.receipt.result !== 'SUCCESS') {
        let reason = info.receipt.result;
        // 尝试解码 resMessage（hex → UTF-8）
        if (info.resMessage) {
            try {
                const decoded = Buffer.from(info.resMessage, 'hex').toString('utf8');
                if (decoded && /^[\x20-\x7E]+$/.test(decoded)) {
                    reason = `${info.receipt.result}: ${decoded}`;
                }
            }
            catch {
                // 解码失败不影响主流程
            }
        }
        return { status: 'failed', reason };
    }
    // 其他情况：无 receipt、receipt 无 result（普通转账）、result=SUCCESS → 已确认
    return { status: 'confirmed' };
}
//# sourceMappingURL=tron-collector.js.map