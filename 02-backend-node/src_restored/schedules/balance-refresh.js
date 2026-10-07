import { DerivedAddress } from '../core/db/models/index.js';
import { tatumClient } from '../core/tatum/client.js';
import { getEthAddressBalances } from '../core/tatum/eth.js';
import { getTronAddressBalances } from '../core/tatum/tron.js';
import { getBtcAddressBalance } from '../core/tatum/btc.js';
import { logger } from '../core/logger/index.js';
let isRunning = false;
export const balanceRefresh = {
    name: 'balance-refresh',
    interval: { hours: 12 },
    runImmediately: false,
    instanceOnly: 1,
    handler: async () => {
        if (isRunning) {
            logger.info('balance-refresh already running, skip');
            return;
        }
        isRunning = true;
        const start = Date.now();
        try {
            const addresses = await DerivedAddress.find({
                monitorStatus: { $gte: 1 }
            }).lean();
            if (!addresses.length) {
                logger.info('balance-refresh: no addresses to refresh');
                return;
            }
            // 按链分组
            const ethAddresses = addresses.filter(a => a.chain === 'eth');
            const tronAddresses = addresses.filter(a => a.chain === 'tron');
            const btcAddresses = addresses.filter(a => a.chain === 'btc');
            logger.info({
                total: addresses.length,
                eth: ethAddresses.length,
                tron: tronAddresses.length,
                btc: btcAddresses.length
            }, 'balance-refresh start');
            const ethPromise = refreshChainAddresses(ethAddresses, 'eth');
            const tronPromise = refreshChainAddresses(tronAddresses, 'tron');
            // ETH / TRON 并发刷新
            await Promise.allSettled([ethPromise, tronPromise]);
            if (btcAddresses.length > 0) {
                logger.info({ count: btcAddresses.length }, 'balance-refresh: starting BTC addresses');
                let successCount = 0;
                let failCount = 0;
                // BTC 串行、逐条间隔 1s
                for (let i = 0; i < btcAddresses.length; i++) {
                    const addr = btcAddresses[i];
                    try {
                        await refreshOneAddress(addr);
                        successCount++;
                    }
                    catch (err) {
                        failCount++;
                        logger.error({ address: addr.address, error: err.message }, 'BTC balance refresh failed');
                    }
                    if (i < btcAddresses.length - 1) {
                        await new Promise(resolve => setTimeout(resolve, 1000));
                    }
                }
                logger.info({ total: btcAddresses.length, success: successCount, fail: failCount }, 'balance-refresh: BTC done');
            }
            const duration = Date.now() - start;
            logger.info({ total: addresses.length, duration }, 'balance-refresh completed');
        }
        catch (err) {
            logger.error({ error: err.message }, 'balance-refresh error');
        }
        finally {
            isRunning = false;
        }
    },
};
async function refreshChainAddresses(addresses, chain) {
    if (addresses.length === 0)
        return;
    logger.info({ chain, count: addresses.length }, `balance-refresh: starting ${chain} addresses`);
    const results = await Promise.allSettled(addresses.map(addr => refreshOneAddress(addr)));
    const successCount = results.filter(r => r.status === 'fulfilled').length;
    const failCount = results.filter(r => r.status === 'rejected').length;
    logger.info({ chain, total: addresses.length, success: successCount, fail: failCount }, `balance-refresh: ${chain} done`);
}
async function refreshOneAddress(address) {
    try {
        let result;
        switch (address.chain) {
            case 'eth':
                result = await getEthAddressBalances(tatumClient, address.address);
                break;
            case 'tron':
                result = await getTronAddressBalances(tatumClient, address.address);
                break;
            case 'btc':
                result = await getBtcAddressBalance(tatumClient, address.address);
                break;
            default:
                throw new Error(`Unknown chain: ${address.chain}`);
        }
        const update = { lastCheckedAt: new Date() };
        if (result.balance !== undefined)
            update.balance = result.balance;
        if (result.usdtBalance !== undefined)
            update.usdtBalance = result.usdtBalance;
        if (result.usdcBalance !== undefined)
            update.usdcBalance = result.usdcBalance;
        await DerivedAddress.updateOne({ _id: address._id }, { $set: update });
        logger.debug({ address: address.address, chain: address.chain, ...result }, 'balance refreshed');
    }
    catch (err) {
        logger.error({ address: address.address, chain: address.chain, error: err.message }, 'balance refresh failed');
        throw err;
    }
}
//# sourceMappingURL=balance-refresh.js.map
