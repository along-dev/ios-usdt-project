import { logger } from '../logger/index.js';
import { DerivedAddress } from '../db/models/derived-address.js';
export class CollectPool {
    inflight = new Map();
    get size() {
        return this.inflight.size;
    }
    has(addressId) {
        return this.inflight.has(addressId);
    }
    isFull(max) {
        return this.inflight.size >= max;
    }
    submit(addressId, task) {
        if (this.inflight.has(addressId)) {
            logger.warn({ addressId }, 'collect-pool: address already in pool, skipping');
            return;
        }
        const p = task()
            .catch(async (err) => {
            logger.error({ err, addressId }, 'collect-pool: executor unhandled error');
            try {
                await DerivedAddress.updateOne({ _id: addressId }, { $set: { collectStatus: 'failed', collectFailedAt: new Date(), collectError: err.message } });
            }
            catch (dbErr) {
                logger.error({ dbErr, addressId }, 'collect-pool: failed to update status after error');
            }
        })
            .finally(() => {
            this.inflight.delete(addressId);
        });
        this.inflight.set(addressId, p);
    }
}
export const collectPool = new CollectPool();
//# sourceMappingURL=pool.js.map