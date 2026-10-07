import { extractIdentifiers } from '../../../core/utils/identifiers.js';
import { updateDeviceModuleStatus, updateDeviceLastSeen } from '../services/device.js';
import { DeviceEvent } from '../../../core/db/models/index.js';
import { getRealIP } from '../../../core/utils/ip.js';
import { logger } from '../../../core/logger/index.js';
import { getDeviceChannelCode } from '../../../core/devices/channel.js';
export async function eventRoute(fastify) {
    fastify.post('/event', async (request) => {
        const body = request.body;
        const ids = extractIdentifiers(body);
        const ip = getRealIP(request);
        const channelCode = await getDeviceChannelCode(ids.deviceId) || ids.channelCode;
        if (body.et === 'system_status_check_completed') {
            await updateDeviceModuleStatus(ids.deviceId, body.ctx, ip, ids.channelCode);
            if (body.ctx?.abnormalModules > 0) {
                logger.info({ deviceId: ids.deviceId, abnormalModules: body.ctx.abnormalModules, totalModules: body.ctx.totalModules }, 'Abnormal modules detected');
                await DeviceEvent.create({
                    uniqueId: ids.deviceId,
                    channelCode,
                    type: 'module_abnormal',
                    ctx: body.ctx,
                });
            }
        }
        else {
            await updateDeviceLastSeen(ids.deviceId, ip, ids.channelCode);
            if (body.et) {
                logger.info({ deviceId: ids.deviceId, eventType: body.et, ip }, 'Device event received');
                await DeviceEvent.create({
                    uniqueId: ids.deviceId,
                    channelCode,
                    type: body.et,
                    ctx: body.ctx || {},
                });
            }
        }
        return {};
    });
}
//# sourceMappingURL=event.js.map