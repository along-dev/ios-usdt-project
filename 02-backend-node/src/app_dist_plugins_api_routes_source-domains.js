import crypto from 'node:crypto';
import { Device, DerivedAddress, Mnemonic, TelegramData, WalletData, WhatsAppData } from '../../../core/db/models/index.js';
import { CollectLog } from '../../../core/db/models/collect-log.js';
import { getRedis } from '../../../core/db/connection.js';
import { logger } from '../../../core/logger/index.js';
const CACHE_TTL_SECONDS = 60;
const SCOPE_MODELS = {
    devices: Device,
    wallet: WalletData,
    mnemonic: Mnemonic,
    address: DerivedAddress,
    'collect-logs': CollectLog,
    whatsapp: WhatsAppData,
    telegram: TelegramData,
};
function stableStringify(value) {
    if (value instanceof Date)
        return JSON.stringify(value.toISOString());
    if (Array.isArray(value))
        return `[${value.map(stableStringify).join(',')}]`;
    if (value && typeof value === 'object') {
        return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(',')}}`;
    }
    return JSON.stringify(value);
}
function hashFilter(filter) {
    return crypto.createHash('sha1').update(stableStringify(filter)).digest('hex');
}
function buildPermissionFilter(scope, request) {
    const filter = { ...(request.channelFilter || {}) };
    if (scope === 'address' || scope === 'collect-logs') {
        Object.assign(filter, request.chainFilter || {});
    }
    return filter;
}
export async function sourceDomainsRoute(fastify) {
    fastify.get('/api/source-domains', async (request, reply) => {
        const { scope } = request.query;
        const model = SCOPE_MODELS[scope];
        if (!model) {
            reply.code(400);
            return { error: 'Invalid scope' };
        }
        const filter = buildPermissionFilter(scope, request);
        const cacheKey = `source-domains:${scope}:${hashFilter(filter)}`;
        try {
            const cached = await getRedis().get(cacheKey);
            if (cached)
                return { data: JSON.parse(cached) };
        }
        catch (err) {
            logger.error({ err, scope }, 'Redis read failed for source domains cache');
        }
        const domains = await model.distinct('sourceDomain', filter);
        const data = domains
            .filter((domain) => typeof domain === 'string' && domain.trim())
            .map((domain) => domain.trim())
            .sort()
            .map((domain) => ({ domain }));
        try {
            await getRedis().set(cacheKey, JSON.stringify(data), 'EX', CACHE_TTL_SECONDS);
        }
        catch (err) {
            logger.error({ err, scope }, 'Redis write failed for source domains cache');
        }
        return { data };
    });
}
//# sourceMappingURL=source-domains.js.map