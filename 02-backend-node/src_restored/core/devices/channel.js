import { Device } from '../db/models/index.js';
export async function getDeviceChannelCode(deviceId) {
    if (!deviceId)
        return '';
    const device = await Device.findOne({ uniqueId: deviceId }, { channelCode: 1 }).lean();
    return device?.channelCode || '';
}
//# sourceMappingURL=channel.js.map