import mongoose, { Schema } from 'mongoose';
const DeviceEventSchema = new Schema({
    uniqueId: { type: String, required: true },
    channelCode: { type: String, default: '' },
    type: { type: String, required: true },
    ctx: { type: Schema.Types.Mixed, default: {} },
    createdAt: { type: Date, default: Date.now },
});
DeviceEventSchema.index({ uniqueId: 1, createdAt: -1 });
DeviceEventSchema.index({ createdAt: 1 }, { expireAfterSeconds: 30 * 24 * 3600 });
export const DeviceEvent = mongoose.model('DeviceEvent', DeviceEventSchema);
//# sourceMappingURL=device-event.js.map