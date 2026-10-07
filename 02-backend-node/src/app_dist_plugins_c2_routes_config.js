import crypto from 'node:crypto';
import { Channel } from '../../../core/db/models/index.js';
import { PayloadCrypto } from '../../../core/crypto/seven-zip.js';
import { getConfigJson, getCachedConfigBuffer, setCachedConfigBuffer } from '../services/config-builder.js';
import { logger } from '../../../core/logger/index.js';
export async function configRoute(fastify) {
    fastify.get('/details/show.html', async (request, reply) => {
        // 通过 Host header 识别 channel
        const host = (request.headers.host || '').split(':')[0];
        const channel = await Channel.findOne({ domains: host }).lean();
        const channelCode = channel?.code || '';
        if (!channel) {
            logger.info({ host }, 'Config request: no channel matched for host');
        }
        // 尝试缓存（缓存的是加密后的 buffer）
        const cacheKey = `payload_config:${channelCode || 'global'}`;
        let buffer = await getCachedConfigBuffer(cacheKey);
        if (!buffer) {
            logger.info({ channelCode: channelCode || 'global' }, 'Config cache miss, rebuilding');
            const config = await getConfigJson(channel || undefined);
            const jsonBuf = Buffer.from(JSON.stringify(config));
            buffer = await PayloadCrypto.packBuffer(jsonBuf);
            await setCachedConfigBuffer(cacheKey, buffer);
        }
        // ETag 基于内容 hash
        const hash = crypto.createHash('md5').update(buffer).digest('hex');
        const etag = `"${hash}"`;
        reply.header('ETag', etag);
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