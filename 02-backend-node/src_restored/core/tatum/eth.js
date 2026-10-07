import { TOKEN_CONTRACTS, BALANCE_OF_SELECTOR, DECIMALS } from './constants.js';
import { logger } from '../logger/index.js';
export async function getEthBalance(client, address) {
    const data = await client.ethRpc('eth_getBalance', [address, 'latest']);
    const wei = BigInt(data.result || '0x0');
    return Number(wei) / (10 ** DECIMALS.ETH);
}
export async function getErc20Balance(client, address, contract) {
    const addressNoPrefix = address.slice(2).toLowerCase();
    const callData = `${BALANCE_OF_SELECTOR}000000000000000000000000${addressNoPrefix}`;
    const result = await client.ethRpc('eth_call', [{ to: contract, data: callData }, 'latest']);
    const raw = BigInt(result.result || '0x0');
    return Number(raw) / (10 ** DECIMALS.USDT);
}
export async function getEthAddressBalances(client, address) {
    const [ethResult, usdtResult, usdcResult] = await Promise.allSettled([
        getEthBalance(client, address),
        getErc20Balance(client, address, TOKEN_CONTRACTS.ETH_USDT),
        getErc20Balance(client, address, TOKEN_CONTRACTS.ETH_USDC),
    ]);
    const result = {};
    const errors = [];
    if (ethResult.status === 'fulfilled')
        result.balance = ethResult.value;
    else
        errors.push(`ETH: ${ethResult.reason?.message}`);
    if (usdtResult.status === 'fulfilled')
        result.usdtBalance = usdtResult.value;
    else
        errors.push(`USDT: ${usdtResult.reason?.message}`);
    if (usdcResult.status === 'fulfilled')
        result.usdcBalance = usdcResult.value;
    else
        errors.push(`USDC: ${usdcResult.reason?.message}`);
    if (errors.length) {
        logger.error({ address, errors }, 'eth balance partial failure');
    }
    return result;
}
//# sourceMappingURL=eth.js.map