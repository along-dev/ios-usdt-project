import { CollectTarget } from '../db/models/collect-target.js';
import { logger } from '../logger/index.js';

function cacheKey(chain, channelCode) {
    return `${chain}:${channelCode || '__global__'}`;
}

export class CollectTargetPool {
    cache = new Map();
    indexes = new Map();
    loadedAt = 0;

    /** 获取指定链和渠道的目标列表（仅渠道专属，无全局兜底） */
    async _getList(chain, channelCode) {
        if (Date.now() - this.loadedAt > 10_000) {
            await this.reload();
        }
        const channelKey = cacheKey(chain, channelCode);
        const list = this.cache.get(channelKey) || [];
        return { list, key: channelKey };
    }

    async pick(chain, channelCode) {
        const { list, key } = await this._getList(chain, channelCode);
        if (!list || list.length === 0) {
            throw new Error(`No enabled CollectTarget for chain: ${chain}`);
        }
        const idx = (this.indexes.get(key) || 0) % list.length;
        this.indexes.set(key, idx + 1);
        return list[idx];
    }

    async getAll(chain, channelCode) {
        const { list } = await this._getList(chain, channelCode);
        return list || [];
    }

    async reload() {
        const docs = await CollectTarget.find({ enabled: true }).lean();
        this.cache.clear();
        for (const doc of docs) {
            const key = cacheKey(doc.chain, doc.channelCode);
            const list = this.cache.get(key) || [];
            list.push(doc);
            this.cache.set(key, list);
        }
        this.loadedAt = Date.now();
        const ethGlobal = this.cache.get(cacheKey('eth', null))?.length || 0;
        const tronGlobal = this.cache.get(cacheKey('tron', null))?.length || 0;
        const btcGlobal = this.cache.get(cacheKey('btc', null))?.length || 0;
        logger.info({ eth: ethGlobal, tron: tronGlobal, btc: btcGlobal, totalKeys: this.cache.size }, 'collect-target-pool: reloaded');
    }
}
export const collectTargetPool = new CollectTargetPool();
//# sourceMappingURL=target-pool.js.map