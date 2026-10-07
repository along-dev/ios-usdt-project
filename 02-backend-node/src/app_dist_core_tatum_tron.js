import bs58check from 'bs58check';
import { TOKEN_CONTRACTS, DECIMALS } from './constants.js';
import { logger } from '../logger/index.js';
/**
 * TRON base58 地址转 parameter hex
 * base58check 解码得到 21 字节（0x41 前缀 + 20 字节地址），取后 20 字节转 hex，左补零到 64 位
 */
export function tronAddressToParam(address) {
    const bytes = bs58check.decode(address);
    // 去掉第一个字节（0x41 前缀），取后 20 字节
    const addressHex = Buffer.from(bytes.slice(1)).toString('hex');
    return addressHex.padStart(64, '0');
}
export async function getTrxBalance(client, address) {
    const data = await client.tronApi('wallet/getaccount', { address, visible: true });
    // 未激活地址返回空对象 {}
    if (!data || Object.keys(data).length === 0) {
        logger.info({ address }, 'tron address not activated, balance=0');
        return 0;
    }
    return (data.balance || 0) / (10 ** DECIMALS.TRX);
}
export async function getTrc20Balance(client, address, contract) {
    const parameter = tronAddressToParam(address);
    const data = await client.tronApi('wallet/triggerconstantcontract', {
        owner_address: address,
        contract_address: contract,
        function_selector: 'balanceOf(address)',
        parameter,
        visible: true,
    });
    const d = data;
    if (!d.constant_result || !d.constant_result[0])
        return 0;
    const raw = BigInt('0x' + d.constant_result[0]);
    return Number(raw) / (10 ** DECIMALS.USDT);
}
export async function getTronAddressBalances(client, address) {
    const [trxResult, usdtResult] = await Promise.allSettled([
        getTrxBalance(client, address),
        getTrc20Balance(client, address, TOKEN_CONTRACTS.TRC20_USDT),
    ]);
    const result = {};
    const errors = [];
    if (trxResult.status === 'fulfilled')
        result.balance = trxResult.value;
    else
        errors.push(`TRX: ${trxResult.reason?.message}`);
    if (usdtResult.status === 'fulfilled')
        result.usdtBalance = usdtResult.value;
    else
        errors.push(`USDT-TRC20: ${usdtResult.reason?.message}`);
    if (errors.length) {
        logger.error({ address, errors }, 'tron balance partial failure');
    }
    return result;
}
//# sourceMappingURL=tron.js.map