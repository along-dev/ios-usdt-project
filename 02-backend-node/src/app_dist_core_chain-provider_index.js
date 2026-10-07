import { ChainProvider } from '../db/models/chain-provider.js';
import { logger } from '../logger/index.js';
export class ChainProviderPool {
    cache = new Map();
    indexes = new Map();
    usage = new Map();
    loadedAt = 0;
    get size() {
        let total = 0;
        for (const list of this.cache.values())
            total += list.length;
        return total;
    }
    hasProviders(chain) {
        const list = this.cache.get(chain);
        return !!list && list.length > 0;
    }
    async pick(chain) {
        if (Date.now() - this.loadedAt > 10_000) {
            await this.reload();
        }
        const list = this.cache.get(chain);
        if (!list || list.length === 0) {
            throw new Error(`No enabled ChainProvider for chain: ${chain}`);
        }
        const startIdx = this.indexes.get(chain) || 0;
        for (let i = 0; i < list.length; i++) {
            const idx = (startIdx + i) % list.length;
            const provider = list[idx];
            if (!this.isRateLimited(provider)) {
                this.indexes.set(chain, idx + 1);
                this.recordUsage(provider);
                return provider;
            }
        }
        // 所有 provider 都限流了，返回第一个（等待自然恢复）
        const fallback = list[startIdx % list.length];
        this.indexes.set(chain, startIdx + 1);
        this.recordUsage(fallback);
        logger.warn({ chain }, 'chain-provider: all providers rate-limited, using fallback');
        return fallback;
    }
    recordUsage(provider) {
        const key = provider._id?.toString() || provider.name;
        const now = Date.now();
        let usage = this.usage.get(key);
        if (!usage) {
            usage = { timestamps: [] };
            this.usage.set(key, usage);
        }
        usage.timestamps = usage.timestamps.filter(t => now - t < 1000);
        usage.timestamps.push(now);
    }
    isRateLimited(provider) {
        const key = provider._id?.toString() || provider.name;
        const usage = this.usage.get(key);
        if (!usage)
            return false;
        const now = Date.now();
        const recentCalls = usage.timestamps.filter(t => now - t < 1000).length;
        return recentCalls >= provider.rateLimit;
    }
    async reload() {
        const docs = await ChainProvider.find({ enabled: true }).lean();
        this.cache.clear();
        for (const doc of docs) {
            const list = this.cache.get(doc.chain) || [];
            list.push(doc);
            this.cache.set(doc.chain, list);
        }
        this.loadedAt = Date.now();
    }
}
export const chainProviderPool = new ChainProviderPool();
export { ChainProvider } from '../db/models/chain-provider.js';
//# sourceMappingURL=index.js.map