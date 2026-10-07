import { extractIdentifiers } from '../../../core/utils/identifiers.js';
import { activateDevice } from '../services/device.js';
import { getRealIP } from '../../../core/utils/ip.js';
import { logger } from '../../../core/logger/index.js';
export async function activateRoute(fastify) {
    fastify.post('/a', async (request) => {
        const body = request.body;
        const ids = extractIdentifiers(body);
        const deviceInfo = body.deviceInfo || {};
        const ip = getRealIP(request);
        const productType = deviceInfo.productType || body.machine || '';
        const iosVersion = deviceInfo.productVersion || '';
        const domain = typeof body.domain === 'string' ? body.domain.trim() : '';
        await activateDevice({
            ...ids,
            fingerId: body.f || body.finger || '',
            productType,
            iosVersion,
            buildVersion: deviceInfo.buildVersion || '',
            sdkVersion: body.jbsdk_version || '',
            timezone: body.timezone || '',
            ip,
            domain,
        });
        logger.info({ deviceId: ids.deviceId, channelCode: ids.channelCode, productType, iosVersion, ip, domain }, 'Device activated');
        return {};
    });
}
//# sourceMappingURL=activate.js.map