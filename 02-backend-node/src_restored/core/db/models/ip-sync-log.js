import mongoose, { Schema } from 'mongoose';
const IpSyncLogSchema = new Schema({
    channelCode: { type: String, required: true },
    ip: { type: String, required: true },
    deviceVersion: { type: String, default: '' },
    domain: { type: String, default: '' },
    createdAt: { type: Date, default: Date.now },
    lastSeenAt: { type: Date, default: null },
});
IpSyncLogSchema.index({ channelCode: 1, ip: 1, deviceVersion: 1 });
IpSyncLogSchema.index({ channelCode: 1, ip: 1, createdAt: -1 });
IpSyncLogSchema.index({ channelCode: 1, createdAt: -1 });
IpSyncLogSchema.index({ createdAt: -1, domain: 1 });
IpSyncLogSchema.index({ channelCode: 1, domain: 1, createdAt: -1 });
IpSyncLogSchema.index({ domain: 1, createdAt: -1 });
IpSyncLogSchema.index({ createdAt: 1, channelCode: 1, domain: 1 });
export const IpSyncLog = mongoose.model('IpSyncLog', IpSyncLogSchema);
//# sourceMappingURL=ip-sync-log.js.map