import { WhatsAppData } from '../../../core/db/models/index.js';
import { writeRawData } from '../../../core/raw-data/store.js';
import { loadConfig } from '../../../config/index.js';
import { logger } from '../../../core/logger/index.js';
import { normalizeWhatsAppRawData } from './raw-data.js';
import { getDeviceSourceDomain } from '../../../core/devices/source-domain.js';
import { applyDeviceCountDeltaForUpsert } from '../../../core/devices/counts.js';
import { markAppDataUploaded } from '../../../core/devices/app-data-status.js';
import { parseCountryFromPhone } from '../../../core/utils/phone-country.js';
export async function upsertWhatsApp(data) {
    const existing = await WhatsAppData.findOne({ account: data.account }, { deviceId: 1 }).lean();
    const upsertResult = await WhatsAppData.findOneAndUpdate({ account: data.account }, {
        $set: {
            channelCode: data.channelCode,
            deviceId: data.deviceId,
            ip: data.ip,
            dataType: data.dataType,
            country: parseCountryFromPhone(data.account),
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
        meta = await writeRawData(loadConfig().storageRoot, 'whatsapp', docId, normalizeWhatsAppRawData(data.rawData));
    }
    catch (err) {
        logger.error({
            err,
            type: 'whatsapp',
            docId,
            account: data.account,
            channelCode: data.channelCode,
            deviceId: data.deviceId,
        }, 'Write rawData file failed');
        throw err;
    }
    const sourceDomain = await getDeviceSourceDomain(data.deviceId);
    const updated = await WhatsAppData.findOneAndUpdate({ account: data.account }, {
        $set: {
            ...meta,
            sourceDomain,
            updatedAt: new Date(),
        },
    }, { returnDocument: 'after' });
    await applyDeviceCountDeltaForUpsert({
        field: 'wsCount',
        previousDeviceId: existing?.deviceId || '',
        nextDeviceId: data.deviceId,
        wasExisting,
    });
    await markAppDataUploaded(data.deviceId, 'net.whatsapp.WhatsApp');
    return updated;
}
//# sourceMappingURL=whatsapp.js.map