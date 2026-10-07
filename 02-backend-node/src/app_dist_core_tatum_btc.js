import { logger } from '../logger/index.js';
export async function getBtcBalance(client, address) {
    const data = await client.btcBalance(address);
    if (!data || !data.balance)
        return 0;
    // Data API 返回字符串格式的余额（satoshi 或已格式化，需要确认）
    const balance = parseFloat(data.balance);
    return balance;
}
export async function getBtcAddressBalance(client, address) {
    try {
        const balance = await getBtcBalance(client, address);
        return { balance };
    }
    catch (err) {
        logger.error({ address, err: err.message }, 'btc balance query failed');
        throw err;
    }
}
//# sourceMappingURL=btc.js.map