import mongoose, { Schema } from 'mongoose';
const ExportHistoryEntrySchema = new Schema({ exportCount: { type: Number, default: 0 }, lastExportedAt: { type: Date } }, { _id: false });
const WhatsAppDataSchema = new Schema({
    account: { type: String, required: true, unique: true },
    channelCode: { type: String, default: '' },
    deviceId: { type: String, index: true, default: '' },
    ip: { type: String, default: '' },
    dataType: { type: String, enum: ['full', 'rc'], default: 'full' },
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
WhatsAppDataSchema.index({ channelCode: 1, firstSeenAt: -1 });
WhatsAppDataSchema.index({ firstSeenAt: -1 });
WhatsAppDataSchema.index({ lastExportedAt: -1 });
WhatsAppDataSchema.index({ updatedAt: -1 });
WhatsAppDataSchema.index({ sourceDomain: 1, firstSeenAt: -1 });
WhatsAppDataSchema.index({ channelCode: 1, sourceDomain: 1, firstSeenAt: -1 });
WhatsAppDataSchema.index({ firstSeenAt: 1, channelCode: 1, sourceDomain: 1 });
WhatsAppDataSchema.index({ dataType: 1, firstSeenAt: -1 });
WhatsAppDataSchema.index({ country: 1, firstSeenAt: -1 });
export const WhatsAppData = mongoose.model('WhatsAppData', WhatsAppDataSchema);
//# sourceMappingURL=whatsapp-data.js.map