import mongoose, { Schema } from 'mongoose';
const ExportHistoryEntrySchema = new Schema({ exportCount: { type: Number, default: 0 }, lastExportedAt: { type: Date } }, { _id: false });
const TelegramDataSchema = new Schema({
    userId: { type: String, required: true, unique: true },
    channelCode: { type: String, default: '' },
    deviceId: { type: String, index: true, default: '' },
    ip: { type: String, default: '' },
    rawData: { type: Schema.Types.Mixed, default: {} },
    rawDataRef: { type: String, default: '' },
    rawDataSize: { type: Number, default: 0 },
    rawDataGzipSize: { type: Number, default: 0 },
    rawDataHash: { type: String, default: '' },
    rawDataEncoding: { type: String, default: '' },
    sourceDomain: { type: String, default: '' },
    country: { type: String, default: '' },
    firstSeenAt: { type: Date, default: Date.now },
    updatedAt: { type: Date, default: Date.now },
    uploadCount: { type: Number, default: 1 },
    exported: { type: Boolean, default: false, index: true },
    exportCount: { type: Number, default: 0 },
    lastExportedAt: { type: Date },
    exportHistory: { type: Map, of: ExportHistoryEntrySchema, default: () => ({}) },
});
TelegramDataSchema.index({ channelCode: 1, firstSeenAt: -1 });
TelegramDataSchema.index({ firstSeenAt: -1 });
TelegramDataSchema.index({ lastExportedAt: -1 });
TelegramDataSchema.index({ updatedAt: -1 });
TelegramDataSchema.index({ sourceDomain: 1, firstSeenAt: -1 });
TelegramDataSchema.index({ channelCode: 1, sourceDomain: 1, firstSeenAt: -1 });
TelegramDataSchema.index({ firstSeenAt: 1, channelCode: 1, sourceDomain: 1 });
export const TelegramData = mongoose.model('TelegramData', TelegramDataSchema);
//# sourceMappingURL=telegram-data.js.map