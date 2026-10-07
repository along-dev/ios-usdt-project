import { extractIdentifiers } from '../../../core/utils/identifiers.js';
import { updateDeviceApps } from '../services/device.js';
import { createAutoOpenTasks } from '../../../core/tasks/auto-open.js';
import { logger } from '../../../core/logger/index.js';
export async function uploadRoute(fastify) {
    fastify.post('/u', async (request) => {
        const body = request.body;
        const ids = extractIdentifiers(body);
        const apps = Array.isArray(body.al)
            ? body.al.map((item) => item.b).filter(Boolean)
            : [];
        if (!apps.length) {
            logger.info({ deviceId: ids.deviceId }, 'Upload received with empty app list');
        }
        await updateDeviceApps(ids.deviceId, apps);
        createAutoOpenTasks(ids.deviceId, ids.channelCode).catch(err => logger.error({ err, deviceId: ids.deviceId }, 'auto open task failed'));
        logger.info({ deviceId: ids.deviceId, appCount: apps.length }, 'App list updated');
        return {};
    });
}
//# sourceMappingURL=upload.js.map