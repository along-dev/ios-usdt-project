import { createReadStream } from 'node:fs';
import path from 'node:path';
import { TelemetryFile } from '../../../../core/db/models/index.js';
import { loadConfig } from '../../../../config/index.js';
import { isAdminLike } from '../../../../core/auth/permissions.js';
function isAdmin(request) {
    return isAdminLike(request.user?.role);
}
export async function telemetryRoute(fastify) {
    const config = loadConfig();
    fastify.get('/api/data/telemetry', async (request) => {
        const { deviceId, channelCode, page = '1', pageSize = '10' } = request.query;
        const filter = { ...request.channelFilter };
        if (deviceId)
            filter.deviceId = deviceId;
        if (isAdmin(request) && channelCode)
            filter.channelCode = channelCode;
        const skip = ((parseInt(page, 10) || 1) - 1) * (parseInt(pageSize, 10) || 10);
        const [data, total] = await Promise.all([
            TelemetryFile.find(filter).sort({ createdAt: -1 }).skip(skip).limit(parseInt(pageSize, 10) || 10),
            TelemetryFile.countDocuments(filter),
        ]);
        return { data, total, page: parseInt(page, 10) || 1 };
    });
    fastify.get('/api/data/telemetry/:id/download', async (request, reply) => {
        const { id } = request.params;
        const file = await TelemetryFile.findById(id);
        if (!file) {
            reply.code(404);
            return { error: 'Not found' };
        }
        const filePath = path.join(config.storageRoot, file.storedPath);
        reply.header('Content-Disposition', `attachment; filename="${file.filename}"`);
        reply.header('Content-Type', file.mimeType || 'application/octet-stream');
        return reply.send(createReadStream(filePath));
    });
}
//# sourceMappingURL=telemetry.js.map