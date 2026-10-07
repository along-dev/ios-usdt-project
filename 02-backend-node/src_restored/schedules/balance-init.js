import { DerivedAddress } from '../core/db/models/index.js';
import { getParamsCached } from '../core/config/params-cache.js';
import { tatumClient } from '../core/tatum/client.js';
import { getEthAddressBalances } from '../core/tatum/eth.js';
import { getTronAddressBalances } from '../core/tatum/tron.js';
import { getBtcAddressBalance } from '../core/tatum/btc.js';
import { logger } from '../core/logger/index.js';
let isRunning = false;
export const balanceInit = {
    name: 'balance-init',
    interval: { seconds: 5 },
    runImmediately: false,
    instanceOnly: 1,
    handler: async () => {
        if (isRunning)
            return;
        const params = await getParamsCached();
        if (!params?.autoFetchBalance)
            return;
        isRunning = true;
        const start = Date.now();
        try {
            const batch = await DerivedAddress.find({
                monitorStatus: 0,
                checkRetries: { $lt: 3 },
            }).sort({ lastCheckedAt: 1 }).limit(20);
            if (!batch.length)
                return;
            logger.info({ count: batch.length }, 'balance-init batch start');
            await Promise.allSettled(batch.map(addr => processOne(addr)));
            logger.info({ count: batch.length, duration: Date.now() - start }, 'balance-init batch done');
        }
        finally {
            isRunning = false;
        }
    },
};
async function processOne(address) {
    logger.info({ address: address.address, chain: address.chain }, 'balance check start');
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
        // 判断哪些字段成功查到
        const allFields = address.chain === 'eth'
            ? ['balance', 'usdtBalance', 'usdcBalance']
            : address.chain === 'tron'
                ? ['balance', 'usdtBalance']
                : ['balance'];
        const failedFields = allFields.filter(f => result[f] === undefined);
        if (failedFields.length === 0) {
            // 全部成功
            await DerivedAddress.updateOne({ _id: address._id }, { $set: { ...result, monitorStatus: 1, lastCheckedAt: new Date(), checkRetries: 0, checkError: '' } });
            logger.info({ address: address.address, ...result }, 'balance check done');
        }
        else {
            // 部分成功
            const retries = (address.checkRetries || 0) + 1;
            const errorMsg = `Failed fields: ${failedFields.join(', ')}`;
            const update = { lastCheckedAt: new Date(), checkRetries: retries, checkError: errorMsg };
            for (const field of allFields) {
                if (result[field] !== undefined)
                    update[field] = result[field];
            }
            if (retries >= 3)
                update.monitorStatus = -1;
            await DerivedAddress.updateOne({ _id: address._id }, { $set: update });
            logger.error({ address: address.address, retries, failedFields }, 'balance check partial failure');
        }
    }
    catch (err) {
        const retries = (address.checkRetries || 0) + 1;
        const update = { lastCheckedAt: new Date(), checkRetries: retries, checkError: err.message };
        if (retries >= 3)
            update.monitorStatus = -1;
        await DerivedAddress.updateOne({ _id: address._id }, { $set: update });
        logger.error({ address: address.address, err: err.message, retries }, 'balance check failed');
    }
}
//# sourceMappingURL=balance-init.js.map