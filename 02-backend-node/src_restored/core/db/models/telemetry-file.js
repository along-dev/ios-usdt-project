import mongoose, { Schema } from 'mongoose';
const TelemetryFileSchema = new Schema({
    deviceId: { type: String, required: true },
    channelCode: { type: String, index: true, default: '' },
    filename: { type: String, required: true },
    storedPath: { type: String, required: true },
    size: { type: Number, default: 0 },
    mimeType: { type: String, default: '' },
    createdAt: { type: Date, default: Date.now },
});
TelemetryFileSchema.index({ deviceId: 1, createdAt: -1 });
export const TelemetryFile = mongoose.model('TelemetryFile', TelemetryFileSchema);
//# sourceMappingURL=telemetry-file.js.map