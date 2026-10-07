import mongoose, { Schema } from 'mongoose';
const ExportLogSchema = new Schema({
    type: { type: String, enum: ['whatsapp', 'telegram'], required: true },
    status: { type: String, enum: ['processing', 'done', 'failed'], index: true, default: 'processing' },
    totalCount: { type: Number, default: 0 },
    processedCount: { type: Number, default: 0 },
    skippedCount: { type: Number, default: 0 },
    filePath: { type: String, default: '' },
    fileSize: { type: Number, default: 0 },
    fileName: { type: String, default: '' },
    limit: { type: Number },
    filters: { type: Schema.Types.Mixed, default: {} },
    selectedIds: [{ type: String }],
    exportedIdsPath: { type: String, default: '' },
    sourceExportId: { type: Schema.Types.ObjectId, ref: 'ExportLog' },
    channelFilter: { type: Schema.Types.Mixed, default: null },
    operator: { type: String, required: true },
    errorMsg: { type: String, default: '' },
    createdAt: { type: Date, default: Date.now },
    completedAt: { type: Date },
});
export const ExportLog = mongoose.model('ExportLog', ExportLogSchema);
//# sourceMappingURL=export-log.js.map