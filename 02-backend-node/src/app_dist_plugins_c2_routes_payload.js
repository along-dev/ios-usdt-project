import { Payload, Channel } from '../../../core/db/models/index.js';
import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import path from 'node:path';
import { loadConfig } from '../../../config/index.js';
import { logger } from '../../../core/logger/index.js';
export async function payloadRoute(fastify) {
    // 共享模块下载
    fastify.get('/details/:name.js', async (request, reply) => {
        const { name } = request.params;
        const payload = await Payload.findOne({ name, active: true });
        if (!payload || !payload.encryptedPath) {
            logger.info({ name }, 'Payload not found or inactive');
            reply.code(404);
            return { error: 'Not found' };
        }
        const config = loadConfig();
        const filePath = path.join(config.storageRoot, payload.encryptedPath);
        // 标准化 ETag
        const etag = `"${payload.sha256}"`;
        reply.header('ETag', etag);
        reply.header('Cache-Control', 'public, max-age=300, no-transform');
        const ifNoneMatch = request.headers['if-none-match'];
        if (ifNoneMatch && (ifNoneMatch.includes(etag) || ifNoneMatch.includes(`W/${etag}`))) {
            reply.code(304);
            return;
        }
        try {
            const fileStat = await stat(filePath);
            reply.header('Content-Type', 'application/octet-stream');
            reply.header('Content-Length', fileStat.size);
            logger.info({ name, size: fileStat.size }, 'Payload served');
            return reply.send(createReadStream(filePath));
        }
        catch (err) {
            logger.warn({ err, filePath, name }, 'Payload file not accessible');
            reply.code(404);
            return { error: 'File not found' };
        }
    });
    // Per-channel corepayload 下载
    fastify.get('/details/ch/:code/corepayload.js', async (request, reply) => {
        const { code } = request.params;
        const channel = await Channel.findOne({ code }).lean();
        if (!channel) {
            logger.info({ code }, 'Channel corepayload: channel not found');
            reply.code(404);
            return { error: 'Not found' };
        }
        const config = loadConfig();
        const filePath = path.join(config.storageRoot, `channels/${channel.name}/corepayload.js`);
        const etag = `"${channel.corePayloadSha256}"`;
        reply.header('ETag', etag);
        reply.header('Cache-Control', 'public, max-age=300, no-transform');
        const ifNoneMatch = request.headers['if-none-match'];
        if (ifNoneMatch && (ifNoneMatch.includes(etag) || ifNoneMatch.includes(`W/${etag}`))) {
            reply.code(304);
            return;
        }
        try {
            const fileStat = await stat(filePath);
            reply.header('Content-Type', 'application/octet-stream');
            reply.header('Content-Length', fileStat.size);
            logger.info({ code, size: fileStat.size }, 'Channel corepayload served');
            return reply.send(createReadStream(filePath));
        }
        catch (err) {
            logger.warn({ err, filePath, code }, 'Channel corepayload not accessible');
            reply.code(404);
            return { error: 'File not found' };
        }
    });
}
//# sourceMappingURL=payload.js.map