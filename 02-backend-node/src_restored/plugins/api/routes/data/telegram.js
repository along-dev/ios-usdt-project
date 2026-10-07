import { TelegramData } from '../../../../core/db/models/index.js';
import { loadConfig } from '../../../../config/index.js';
import { deleteRawData, readRawDataJson } from '../../../../core/raw-data/store.js';
import { logger } from '../../../../core/logger/index.js';
import { applyDeviceCountDeltaForDelete } from '../../../../core/devices/counts.js';
import { isAdminLike } from '../../../../core/auth/permissions.js';
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
export async function telegramRoute(fastify) {
    fastify.get('/api/data/telegram', async (request) => {
        const { channelCode, userId, deviceId, sourceDomain, exported, updatedAtStart, updatedAtEnd, lastExportedAtStart, lastExportedAtEnd, firstSeenAtStart, firstSeenAtEnd, sortField, sortOrder, page = '1', pageSize = '10' } = request.query;
        const filter = { ...request.channelFilter };
        const admin = isAdmin(request);
        const username = request.user?.username;
        if (isAdmin(request) && channelCode)
            filter.channelCode = channelCode;
        if (userId)
            filter.userId = userId;
        if (deviceId)
            filter.deviceId = deviceId;
        if (sourceDomain)
            filter.sourceDomain = sourceDomain;
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
            TelegramData.find(filter, listProjection).sort(buildListSort(sortField, sortOrder)).skip(skip).limit(parseInt(pageSize, 10) || 10),
            TelegramData.countDocuments(filter),
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
    fastify.get('/api/data/telegram/:id', async (request, reply) => {
        if (!isAdmin(request)) {
            reply.code(403);
            return { error: 'Admin only' };
        }
        const { id } = request.params;
        const r = await TelegramData.findById(id);
        if (!r) {
            reply.code(404);
            return { error: 'Not found' };
        }
        if (!r.rawDataRef) {
            logger.warn({ type: 'telegram', id }, 'Telegram rawDataRef missing');
            reply.code(422);
            return { error: 'Raw data file missing' };
        }
        try {
            const rawData = await readRawDataJson(loadConfig().storageRoot, r.rawDataRef);
            const data = typeof r.toObject === 'function' ? r.toObject() : r;
            return { data: { ...data, rawData } };
        }
        catch (err) {
            logger.error({ err, id, rawDataRef: r.rawDataRef }, 'Read Telegram rawData failed');
            reply.code(500);
            return { error: 'Raw data unavailable' };
        }
    });
    fastify.delete('/api/data/telegram/:id', async (request, reply) => {
        if (!isAdmin(request)) {
            reply.code(403);
            return { error: 'Admin only' };
        }
        const { id } = request.params;
        const r = await TelegramData.findById(id, { rawDataRef: 1, deviceId: 1 });
        const result = await TelegramData.deleteOne({ _id: id });
        if (result.deletedCount > 0) {
            await applyDeviceCountDeltaForDelete({ field: 'tgCount', deviceId: r?.deviceId });
            try {
                await deleteRawData(loadConfig().storageRoot, r?.rawDataRef);
            }
            catch (err) {
                logger.error({ err, type: 'telegram', id, rawDataRef: r?.rawDataRef }, 'Delete Telegram rawData file failed');
                throw err;
            }
        }
        return { success: true };
    });
}
//# sourceMappingURL=telegram.js.map