import { Device, Mnemonic, TelegramData, WhatsAppData } from '../db/models/index.js';
export async function applyDeviceCountDeltaForUpsert(input) {
    const previous = input.previousDeviceId || '';
    const next = input.nextDeviceId || '';
    if (!next)
        return;
    if (!input.wasExisting) {
        await Device.updateOne({ uniqueId: next }, { $inc: { [input.field]: 1 } });
        return;
    }
    if (previous && previous !== next) {
        await Device.updateOne({ uniqueId: previous }, { $inc: { [input.field]: -1 } });
        await Device.updateOne({ uniqueId: next }, { $inc: { [input.field]: 1 } });
    }
}
export async function applyDeviceCountDeltaForDelete(input) {
    if (!input.deviceId)
        return;
    await Device.updateOne({ uniqueId: input.deviceId }, { $inc: { [input.field]: -1 } });
}
async function countsByDevice(model) {
    const rows = await model.aggregate([
        { $match: { deviceId: { $gt: '' } } },
        { $group: { _id: '$deviceId', count: { $sum: 1 } } },
    ]);
    return new Map(rows.map((row) => [row._id, row.count]));
}
export async function recomputeDeviceCounts() {
    const [ws, tg, mnemonic] = await Promise.all([
        countsByDevice(WhatsAppData),
        countsByDevice(TelegramData),
        countsByDevice(Mnemonic),
    ]);
    const deviceIds = new Set([
        ...ws.keys(),
        ...tg.keys(),
        ...mnemonic.keys(),
    ]);
    await Device.updateMany({}, { $set: { wsCount: 0, tgCount: 0, mnemonicCount: 0 } });
    for (const uniqueId of deviceIds) {
        await Device.updateOne({ uniqueId }, {
            $set: {
                wsCount: ws.get(uniqueId) || 0,
                tgCount: tg.get(uniqueId) || 0,
                mnemonicCount: mnemonic.get(uniqueId) || 0,
            },
        });
    }
    return { deviceCount: deviceIds.size };
}
//# sourceMappingURL=counts.js.map