import mongoose, { Schema } from 'mongoose';
const AndroidConfigSchema = new Schema({
    _id: { type: String, default: 'global' },
    template: { type: String, default: 'vodex' },
    theme: { type: String, default: 'rose' },
    pixelIds: { type: [String], default: [] },
    downloadMode: { type: String, default: 'link' },
    apkUrl: { type: String, default: '' },
    updatedAt: { type: Date, default: Date.now },
});
export const AndroidConfig = mongoose.model('AndroidConfig', AndroidConfigSchema);
