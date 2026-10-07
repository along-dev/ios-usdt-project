import crypto from 'node:crypto';
import { Channel } from '../../../core/db/models/index.js';
import { PayloadCrypto } from '../../../core/crypto/seven-zip.js';
import { getConfigJson, getCachedConfigBuffer, setCachedConfigBuffer } from '../services/config-builder.js';
import { pickChain } from '../services/chain-router.js';
import { logger } from '../../../core/logger/index.js';
export async function configRoute(fastify) {
    fastify.get('/details/show.html', async (request, reply) => {
        // 通过 Host header 识别 channel
        const host = (request.headers.host || '').split(':')[0];
        const channel = await Channel.findOne({ domains: host }).lean();
        const channelCode = channel?.code || '';
        if (!channel) {
            // ★ GAP2(a)：Host 未过渠道白名单 ⇒ **不据其拼 URL**（Host 头可伪造）。
            //   改「响亮 unsupported」，并记 WARN（**只含 host，不含 body/凭据**）。
            logger.warn({ host }, 'Config request: host not in any channel allowlist -> unsupported');
        }
        // ★ GAP2(c)：scheme 取**白名单** —— `x-forwarded-proto` 是请求头、可伪造，
        //   只接受 http/https，其余**一律回落 http 并记 WARN**（防 `javascript://` 之类混入 URL）。
        const xfpRaw = String(request.headers['x-forwarded-proto'] || '').split(',')[0].trim().toLowerCase();
        let scheme = 'http';
        if (xfpRaw === 'http' || xfpRaw === 'https') {
            scheme = xfpRaw;
        } else if (xfpRaw) {
            logger.warn({ xfp: xfpRaw, host }, 'Config request: invalid x-forwarded-proto -> fallback http');
        }
        // ★ GAP2(a)：**只有** Host 通过渠道白名单（channel 命中）时才据其构造 origin
        const origin = channel ? `${scheme}://${host}` : null;
        const ua = request.headers['user-agent'] || '';
        // ★ F1-C11：缓存键必须含【设备选链结果】维度。
        //   原实现 `payload_config:${channelCode || 'global'}` 不含设备维度
        //   ⇒ 第一个请求者的 UA 决定所有人的载荷清单（实测：iOS16.5 请求后，
        //     iOS18.4 / 17.5 / Windows 全部拿到 coruna 的清单，md5 完全一致）
        //   ⇒ darksword 设备永远拿不到自己的链，且空白区永远收不到 unsupported 告警
        //     （使 V0 裁决 D-3 的"显式告警"在端到端层面失效）。
        //   用 pickChain 的【结果】（chain:reach）而非原始 UA：
        //     · 同链同 reach 的设备共享缓存（不碎片化）；
        //     · 不同链 / 不支持 各自独立；
        //     · 与 getConfigJson 内部选链使用【同一判据】，不会分叉。
        const route = pickChain(ua);
        const routeKey = route ? `${route.chain}:${route.reach}` : 'unsupported';
        // ★ 前缀必须保持 `payload_config:` —— invalidateConfigCache 用
        //   `KEYS payload_config:*` 通配清除（改前缀会导致失效逻辑漏掉新键）。
        // ★ GAP2(b)：缓存键**必须含 host** —— `Channel.domains` 是数组，
        //   多域名可映射同一 channel；不含 host ⇒ A 域名的配置会被 B 域名命中（设备去 A 取载荷）。
        //   前缀 `payload_config:` 保持不变（invalidateConfigCache 用 `KEYS payload_config:*` 通配）。
        const cacheKey = `payload_config:${channelCode || 'global'}:${routeKey}:${host}`;
        let buffer = await getCachedConfigBuffer(cacheKey);
        if (!buffer) {
            logger.info({ cacheKey, routeKey }, 'Config cache miss, rebuilding');
            // ★ I1-C1：必须把 device 传给 getConfigJson —— 它据此调 pickChain(ua) 选链。
            // ★ GAP2：把**已过白名单校验的 origin** 一并下传（channel 未命中时为 null）。
            const config = await getConfigJson(channel || undefined, { userAgent: ua }, origin);
            // ★ I1-C1：设备不被任何链支持时，不得缓存/下发空配置 —— 显式区分。
            if (config && config.unsupported) {
                logger.info({ ua: String(ua).slice(0, 120) }, 'Config request: unsupported device');
                reply.code(200);
                reply.header('Content-Type', 'application/json');
                return { unsupported: true, reason: config.reason };
            }
            const jsonBuf = Buffer.from(JSON.stringify(config));
            buffer = await PayloadCrypto.packBuffer(jsonBuf);
            await setCachedConfigBuffer(cacheKey, buffer);
        }
        // ETag 基于内容 hash
        const hash = crypto.createHash('md5').update(buffer).digest('hex');
        const etag = `"${hash}"`;
        reply.header('ETag', etag);
        // ★ GAP2(c)：下发的 URL 依赖 Host ⇒ 必须 `Vary: Host`，
        //   否则共享/CDN 缓存会把一个域名的配置发给另一个域名（跨域串味）。
        reply.header('Vary', 'Host');
        reply.header('Cache-Control', 'public, max-age=300, no-transform');
        reply.header('Content-Type', 'application/octet-stream');
        // 304 判断
        const ifNoneMatch = request.headers['if-none-match'];
        if (ifNoneMatch && (ifNoneMatch.includes(etag) || ifNoneMatch.includes(`W/${etag}`))) {
            reply.code(304);
            return;
        }
        return reply.send(buffer);
    });
}
//# sourceMappingURL=config.js.map