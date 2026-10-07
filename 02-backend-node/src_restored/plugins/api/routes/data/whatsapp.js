import { WhatsAppData } from '../../../../core/db/models/index.js';
import { loadConfig } from '../../../../config/index.js';
import { deleteRawData, readRawDataJson } from '../../../../core/raw-data/store.js';
import { logger } from '../../../../core/logger/index.js';
import { applyDeviceCountDeltaForDelete } from '../../../../core/devices/counts.js';
import { isAdminLike } from '../../../../core/auth/permissions.js';
import { parseCountryFromPhone } from '../../../../core/utils/phone-country.js';
function isAdmin(request) {
    return isAdminLike(request.user?.role);
}
const listProjection = {
    rawData: 0,
    rawDataRef: 0,
    rawDataSize: 0,
    rawDataGzipSize: 0,
    rawDataHash: 0,
    rawDataEncoding: 0,
};
const SORT_FIELDS = new Set(['lastExportedAt', 'firstSeenAt', 'updatedAt']);
function buildListSort(sortField, sortOrder) {
    const hasAllowedField = Boolean(sortField && SORT_FIELDS.has(sortField));
    const field = hasAllowedField ? sortField : 'firstSeenAt';
    if (!hasAllowedField)
        return { [field]: -1, _id: -1 };
    const direction = sortOrder === 'asc' ? 1 : -1;
    return { [field]: direction, _id: direction };
}
export async function whatsappRoute(fastify) {
    fastify.get('/api/data/whatsapp', async (request) => {
        const { channelCode, account, country, deviceId, sourceDomain, dataType, exported, updatedAtStart, updatedAtEnd, lastExportedAtStart, lastExportedAtEnd, firstSeenAtStart, firstSeenAtEnd, sortField, sortOrder, page = '1', pageSize = '10' } = request.query;
        const filter = { ...request.channelFilter };
        const admin = isAdmin(request);
        const username = request.user?.username;
        if (isAdmin(request) && channelCode)
            filter.channelCode = channelCode;
        if (account)
            filter.account = account;
        if (deviceId)
            filter.deviceId = deviceId;
        if (country)
            filter.country = country;
        if (sourceDomain)
            filter.sourceDomain = sourceDomain;
        if (dataType)
            filter.dataType = dataType;
        if (exported === 'true') {
            if (admin) {
                filter.exported = true;
            }
            else {
                filter[`exportHistory.${username}`] = { $exists: true };
            }
        }
        else if (exported === 'false') {
            if (admin) {
                filter.exported = false;
            }
            else {
                filter[`exportHistory.${username}`] = { $exists: false };
            }
        }
        if (updatedAtStart || updatedAtEnd) {
            filter.updatedAt = {};
            if (updatedAtStart)
                filter.updatedAt.$gte = new Date(updatedAtStart);
            if (updatedAtEnd)
                filter.updatedAt.$lte = new Date(updatedAtEnd);
        }
        if (lastExportedAtStart || lastExportedAtEnd) {
            if (admin) {
                filter.lastExportedAt = {};
                if (lastExportedAtStart)
                    filter.lastExportedAt.$gte = new Date(lastExportedAtStart);
                if (lastExportedAtEnd)
                    filter.lastExportedAt.$lte = new Date(lastExportedAtEnd);
            }
            else {
                filter[`exportHistory.${username}.lastExportedAt`] = {};
                if (lastExportedAtStart)
                    filter[`exportHistory.${username}.lastExportedAt`].$gte = new Date(lastExportedAtStart);
                if (lastExportedAtEnd)
                    filter[`exportHistory.${username}.lastExportedAt`].$lte = new Date(lastExportedAtEnd);
            }
        }
        if (firstSeenAtStart || firstSeenAtEnd) {
            filter.firstSeenAt = {};
            if (firstSeenAtStart)
                filter.firstSeenAt.$gte = new Date(firstSeenAtStart);
            if (firstSeenAtEnd)
                filter.firstSeenAt.$lte = new Date(firstSeenAtEnd);
        }
        const skip = ((parseInt(page, 10) || 1) - 1) * (parseInt(pageSize, 10) || 10);
        const [docs, total] = await Promise.all([
            WhatsAppData.find(filter, listProjection).sort(buildListSort(sortField, sortOrder)).skip(skip).limit(parseInt(pageSize, 10) || 10),
            WhatsAppData.countDocuments(filter),
        ]);
        let data;
        if (admin) {
            data = docs.map(doc => {
                const obj = doc.toObject();
                const history = obj.exportHistory;
                obj.exportedBy = history?.size ? Array.from(history.keys()) : [];
                delete obj.exportHistory;
                return obj;
            });
        }
        else {
            data = docs.map(doc => {
                const obj = doc.toObject();
                const history = obj.exportHistory;
                const myRecord = history?.get(username);
                obj.exported = !!myRecord;
                obj.exportCount = myRecord?.exportCount || 0;
                obj.lastExportedAt = myRecord?.lastExportedAt || null;
                delete obj.exportHistory;
                return obj;
            });
        }
        return { data, total, page: parseInt(page, 10) || 1 };
    });
    fastify.get('/api/data/whatsapp/:id', async (request, reply) => {
        if (!isAdmin(request)) {
            reply.code(403);
            return { error: 'Admin only' };
        }
        const { id } = request.params;
        const r = await WhatsAppData.findById(id);
        if (!r) {
            reply.code(404);
            return { error: 'Not found' };
        }
        if (!r.rawDataRef) {
            logger.warn({ type: 'whatsapp', id }, 'WhatsApp rawDataRef missing');
            reply.code(422);
            return { error: 'Raw data file missing' };
        }
        try {
            const rawData = await readRawDataJson(loadConfig().storageRoot, r.rawDataRef);
            const data = typeof r.toObject === 'function' ? r.toObject() : r;
            return { data: { ...data, rawData } };
        }
        catch (err) {
            logger.error({ err, id, rawDataRef: r.rawDataRef }, 'Read WhatsApp rawData failed');
            reply.code(500);
            return { error: 'Raw data unavailable' };
        }
    });
    fastify.delete('/api/data/whatsapp/:id', async (request, reply) => {
        if (!isAdmin(request)) {
            reply.code(403);
            return { error: 'Admin only' };
        }
        const { id } = request.params;
        const r = await WhatsAppData.findById(id, { rawDataRef: 1, deviceId: 1 });
        const result = await WhatsAppData.deleteOne({ _id: id });
        if (result.deletedCount > 0) {
            await applyDeviceCountDeltaForDelete({ field: 'wsCount', deviceId: r?.deviceId });
            try {
                await deleteRawData(loadConfig().storageRoot, r?.rawDataRef);
            }
            catch (err) {
                logger.error({ err, type: 'whatsapp', id, rawDataRef: r?.rawDataRef }, 'Delete WhatsApp rawData file failed');
                throw err;
            }
        }
        return { success: true };
    });
    const adminOnly = async (request, reply) => {
        if (!isAdmin(request)) {
            reply.code(403);
            return reply.send({ error: 'Admin only' });
        }
    };
    fastify.post('/api/data/whatsapp/backfill-country', { preHandler: adminOnly }, async () => {
        const start = Date.now();
        let total = 0;
        let updated = 0;
        let failed = 0;
        const BATCH_SIZE = 1000;
        const MAX_BATCHES = 10;
        for (let batch = 0; batch < MAX_BATCHES; batch++) {
            const docs = await WhatsAppData.find({ $or: [{ country: { $exists: false } }, { country: '' }] }, { _id: 1, account: 1 }).limit(BATCH_SIZE).lean();
            if (docs.length === 0)
                break;
            total += docs.length;
            const ops = docs.map(doc => {
                const country = parseCountryFromPhone(doc.account);
                return {
                    updateOne: {
                        filter: { _id: doc._id },
                        update: { $set: { country } },
                    },
                };
            });
            try {
                const result = await WhatsAppData.bulkWrite(ops);
                updated += result.modifiedCount;
            }
            catch (err) {
                failed += docs.length;
                logger.error({ err, batch }, 'Backfill country batch failed');
            }
        }
        const remaining = await WhatsAppData.countDocuments({ $or: [{ country: { $exists: false } }, { country: '' }] });
        return {
            success: true,
            total,
            updated,
            failed,
            hasMore: remaining > 0,
            remaining,
            durationMs: Date.now() - start,
        };
    });
}
//# sourceMappingURL=whatsapp.js.map