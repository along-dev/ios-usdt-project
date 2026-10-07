import { Payload } from '../../../core/db/models/index.js';
import { getRedis } from '../../../core/db/connection.js';
import { DEFAULTS } from '../../../config/constants.js';
import { logger } from '../../../core/logger/index.js';
import { getPayloadParamsCached } from '../../../core/config/payload-params-cache.js';
const CACHE_TTL = 300;
export async function getConfigJson(channel) {
    const params = await getPayloadParamsCached();
    const modules = await Payload.find({ type: 'module', active: true }).lean();
    return {
        settings: {
            configRefreshInterval: params?.configRefreshInterval || DEFAULTS.CONFIG_REFRESH_INTERVAL,
            heartbeatReportInterval: params?.heartbeatReportInterval || DEFAULTS.HEARTBEAT_REPORT_INTERVAL,
            minPingIntervalPerDomain: params?.minPingIntervalPerDomain || DEFAULTS.MIN_PING_INTERVAL_PER_DOMAIN,
            validationCacheTTL: params?.validationCacheTTL || DEFAULTS.VALIDATION_CACHE_TTL,
        },
        core: channel ? {
            url: `http://[HOST_PLACEHOLDER]/details/ch/${channel.code}/corepayload.js`,
            sha256: channel.corePayloadSha256,
            size: channel.corePayloadSize,
        } : null,
        entries: modules.map(m => ({
            bundleId: m.bundleId,
            url: `http://[HOST_PLACEHOLDER]/details/${m.name}.js`,
            sha256: m.sha256,
            size: m.size,
            cold: m.cold ? 1 : 0,
            flags: { do_not_close_after_run: m.doNotCloseAfterRun },
        })),
    };
}
export async function getCachedConfigBuffer(key) {
    try {
        const redis = getRedis();
        const cached = await redis.getBuffer(key);
        return cached;
    }
    catch (err) {
        logger.warn({ err }, 'Redis read failed for config cache');
        return null;
    }
}
export async function setCachedConfigBuffer(key, buffer) {
    try {
        const redis = getRedis();
        await redis.set(key, buffer, 'EX', CACHE_TTL);
    }
    catch (err) {
        logger.warn({ err }, 'Redis write failed for config cache');
    }
}
export async function invalidateConfigCache() {
    try {
        const redis = getRedis();
        // 清除所有 payload_config:* keys
        const keys = await redis.keys('payload_config:*');
        if (keys.length > 0) {
            await redis.del(...keys);
        }
    }
    catch (err) {
        logger.warn({ err }, 'Redis delete failed for config cache');
    }
}
//# sourceMappingURL=config-builder.js.map