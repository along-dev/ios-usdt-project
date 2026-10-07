import { DerivedAddress } from '../core/db/models/index.js';
import { getParamsCached } from '../core/config/params-cache.js';
import { tatumClient } from '../core/tatum/client.js';
import { TATUM_CHAIN_IDS } from '../core/tatum/constants.js';
import { logger } from '../core/logger/index.js';
let isRunning = false;
export const subscriptionSync = {
    name: 'subscription-sync',
    interval: { seconds: 5 },
    runImmediately: false,
    instanceOnly: 1,
    handler: async (config) => {
        if (isRunning)
            return;
        const params = await getParamsCached();
        if (!params?.tatumAutoSubscribe)
            return;
        isRunning = true;
        const start = Date.now();
        try {
            if (!config.tatumWebhookUrl) {
                logger.info('TATUM_WEBHOOK_URL not configured, skipping subscription-sync');
                return;
            }
            const batch = await DerivedAddress.find({ monitorStatus: 1 })
                .sort({ lastSubscribeTime: 1 })
                .limit(20);
            if (!batch.length)
                return;
            logger.info({ count: batch.length }, 'subscription-sync batch start');
            await Promise.allSettled(batch.map(addr => subscribe(addr, config.tatumWebhookUrl)));
            logger.info({ count: batch.length, duration: Date.now() - start }, 'subscription-sync batch done');
        }
        finally {
            isRunning = false;
        }
    },
};
async function subscribe(address, webhookUrl) {
    const now = new Date();
    const chainId = TATUM_CHAIN_IDS[address.chain];
    if (!chainId) {
        logger.error({ address: address.address, chain: address.chain }, 'unknown chain for subscription');
        return;
    }
    logger.info({ address: address.address, chain: address.chain }, 'subscription creating');
    try {
        const { subscriptionId, keyId } = await tatumClient.createSubscription(address.address, chainId, webhookUrl);
        await DerivedAddress.updateOne({ _id: address._id }, { $set: { monitorStatus: 2, subscriptionId, lastSubscribeTime: now, tatumKeyId: keyId, subscribeRetries: 0, subscribeError: '' } });
        logger.info({ address: address.address, subscriptionId }, 'subscription created');
    }
    catch (err) {
        const retries = (address.subscribeRetries || 0) + 1;
        if (retries >= 3) {
            await DerivedAddress.updateOne({ _id: address._id }, { $set: { monitorStatus: -2, subscribeRetries: retries, lastSubscribeTime: now, subscribeError: err.message } });
            logger.error({ address: address.address, retries, err: err.message }, 'subscription permanently failed');
        }
        else {
            await DerivedAddress.updateOne({ _id: address._id }, { $set: { subscribeRetries: retries, lastSubscribeTime: now, subscribeError: err.message } });
            logger.error({ address: address.address, retries, err: err.message }, 'subscription creation failed, will retry');
        }
    }
}
//# sourceMappingURL=subscription-sync.js.map