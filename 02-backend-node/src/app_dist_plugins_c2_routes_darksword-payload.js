import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import path from 'node:path';
import { DarkswordPayload } from '../../../core/db/models/index.js';
import { loadConfig } from '../../../config/index.js';
import { logger } from '../../../core/logger/index.js';
export async function darkswordPayloadRoute(fastify) {
    fastify.get('/details/ds/:name.js', async (request, reply) => {
        const { name } = request.params;
        const payload = await DarkswordPayload.findOne({ name, active: true });
        if (!payload || !payload.encryptedPath) {
            reply.code(404);
            return { error: 'Not found' };
        }
        const config = loadConfig();
        const filePath = path.join(config.storageRoot, payload.encryptedPath);
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
            logger.info({ name, size: fileStat.size }, 'Darksword payload served');
            return reply.send(createReadStream(filePath));
        }
        catch (err) {
            logger.warn({ err, filePath, name }, 'Darksword payload file not accessible');
            reply.code(404);
            return { error: 'File not found' };
        }
    });
}
//# sourceMappingURL=darksword-payload.js.map