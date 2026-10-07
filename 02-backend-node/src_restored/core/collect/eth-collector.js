import { JsonRpcProvider, Wallet } from 'ethers';
import { chainProviderPool } from '../chain-provider/index.js';
import { logger } from '../logger/index.js';
import { withRetry, isEthRateLimitError } from './rpc-retry.js';
import { toHumanReadable, DECIMALS, } from './types.js';
const USDT_CONTRACT = '0xdAC17F958D2ee523a2206206994597C13D831ec7';
const USDC_CONTRACT = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48';
// ERC-20 function selectors
const BALANCE_OF_SELECTOR = '0x70a08231';
const TRANSFER_SELECTOR = '0xa9059cbb';
// --- Helpers ---
async function getProvider() {
    const { baseUrl } = await chainProviderPool.pick('eth');
    const provider = new JsonRpcProvider(baseUrl);
    const originalSend = provider.send.bind(provider);
    provider.send = async (method, params) => {
        logger.info({ method, params }, 'eth-rpc: request');
        const result = await withRetry(() => originalSend(method, params), { maxRetries: 1, delayMs: 3000, label: `eth ${method}`, isRetryable: isEthRateLimitError });
        logger.info({ method, result: typeof result === 'string' && result.length > 200 ? result.slice(0, 200) + '...' : result }, 'eth-rpc: response');
        return result;
    };
    return provider;
}
export function encodeBalanceOf(address) {
    const addr = address.toLowerCase().replace('0x', '').padStart(64, '0');
    return BALANCE_OF_SELECTOR + addr;
}
export function encodeTransfer(to, amount) {
    const addr = to.toLowerCase().replace('0x', '').padStart(64, '0');
    const value = amount.toString(16).padStart(64, '0');
    return TRANSFER_SELECTOR + addr + value;
}
// --- Exported Functions ---
export async function queryBalances(address) {
    const provider = await getProvider();
    const [native, usdt, usdc] = await Promise.all([
        provider.getBalance(address),
        provider.call({ to: USDT_CONTRACT, data: encodeBalanceOf(address) }),
        provider.call({ to: USDC_CONTRACT, data: encodeBalanceOf(address) }),
    ]);
    return {
        native,
        usdt: BigInt(usdt || '0x0'),
        usdc: BigInt(usdc || '0x0'),
    };
}
export async function detectMultisig(address) {
    const provider = await getProvider();
    const code = await provider.getCode(address);
    if (code && code !== '0x') {
        return { isMultisig: true, reason: '合约地址：检测到 bytecode' };
    }
    return { isMultisig: false, reason: '' };
}
export async function estimateGas(provider, txData) {
    const [block, feeData] = await Promise.all([
        provider.getBlock('latest'),
        provider.getFeeData(),
    ]);
    const baseFee = block.baseFeePerGas;
    const maxPriorityFeePerGas = feeData.maxPriorityFeePerGas ?? 1500000000n;
    let gasLimit;
    if (txData.data) {
        // ERC-20 transfer: estimate + 1.2x safety margin
        const estimated = await provider.estimateGas(txData);
        gasLimit = estimated * 120n / 100n;
    }
    else {
        // Native ETH transfer
        gasLimit = 21000n;
    }
    const maxFeePerGas = baseFee * 2n + maxPriorityFeePerGas;
    const totalMaxCost = gasLimit * maxFeePerGas;
    return { gasLimit, maxFeePerGas, maxPriorityFeePerGas, totalMaxCost };
}
export async function transferNative(params) {
    const { privateKey, fromAddress, toAddress, balance, gasCommitted, nonce: externalNonce } = params;
    const provider = await getProvider();
    const wallet = new Wallet('0x' + privateKey, provider);
    const [block, feeData] = await Promise.all([
        provider.getBlock('latest'),
        provider.getFeeData(),
    ]);
    const resolvedNonce = externalNonce ?? await provider.getTransactionCount(fromAddress, 'pending');
    const baseFee = block.baseFeePerGas;
    const maxPriorityFeePerGas = feeData.maxPriorityFeePerGas ?? 1500000000n;
    const maxFeePerGas = baseFee * 2n + maxPriorityFeePerGas;
    const gasLimit = 21000n;
    const amount = balance - gasCommitted - maxFeePerGas * gasLimit;
    if (amount <= 0n) {
        throw new Error('insufficient: ETH balance too low after gas commitment');
    }
    const tx = await wallet.sendTransaction({
        type: 2,
        to: toAddress,
        value: amount,
        nonce: resolvedNonce,
        gasLimit,
        maxFeePerGas,
        maxPriorityFeePerGas,
        chainId: 1,
    });
    const fee = toHumanReadable(maxFeePerGas * gasLimit, DECIMALS.ETH);
    const amountStr = toHumanReadable(amount, DECIMALS.ETH);
    logger.info({ txHash: tx.hash, amount: amountStr, nonce: resolvedNonce, token: 'ETH' }, 'eth-collector: native transfer sent');
    return { txHash: tx.hash, amount: amountStr, fee };
}
export async function transferErc20(params) {
    const { privateKey, fromAddress, toAddress, tokenBalance, token, nonce, gasCommitted } = params;
    const contractAddress = token === 'usdt' ? USDT_CONTRACT : USDC_CONTRACT;
    const provider = await getProvider();
    const wallet = new Wallet('0x' + privateKey, provider);
    const data = encodeTransfer(toAddress, tokenBalance);
    const gasEstimate = await estimateGas(provider, {
        from: fromAddress,
        to: contractAddress,
        data,
    });
    // Check ETH balance can cover gas (including previously committed gas)
    const ethBalance = await provider.getBalance(fromAddress);
    if (ethBalance < gasEstimate.totalMaxCost + gasCommitted) {
        throw new Error('insufficient: ETH balance cannot cover gas for ERC-20 transfer');
    }
    const tx = await wallet.sendTransaction({
        type: 2,
        to: contractAddress,
        data,
        nonce,
        gasLimit: gasEstimate.gasLimit,
        maxFeePerGas: gasEstimate.maxFeePerGas,
        maxPriorityFeePerGas: gasEstimate.maxPriorityFeePerGas,
        chainId: 1,
    });
    const fee = toHumanReadable(gasEstimate.totalMaxCost, DECIMALS.ETH);
    const amountStr = toHumanReadable(tokenBalance, DECIMALS[token.toUpperCase()]);
    logger.info({ txHash: tx.hash, amount: amountStr, nonce, token: token.toUpperCase() }, 'eth-collector: ERC-20 transfer sent');
    return { result: { txHash: tx.hash, amount: amountStr, fee }, gasCost: gasEstimate.totalMaxCost };
}
export async function getNonce(address) {
    const provider = await getProvider();
    return provider.getTransactionCount(address, 'pending');
}
export async function getTransactionStatus(txHash) {
    const provider = await getProvider();
    const receipt = await provider.getTransactionReceipt(txHash);
    if (!receipt)
        return { status: 'pending' };
    if (receipt.status === 1)
        return { status: 'confirmed' };
    return { status: 'failed', reason: 'execution reverted' };
}
//# sourceMappingURL=eth-collector.js.map