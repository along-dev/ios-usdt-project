import mongoose, { Schema } from 'mongoose';
const ParamsSchema = new Schema({
    _id: { type: String, default: 'global' },
    autoFetchBalance: { type: Boolean, default: false },
    tatumAutoSubscribe: { type: Boolean, default: false },
    updatedAt: { type: Date, default: Date.now },
    collectEnabled: { type: Boolean, default: false },
    collectConcurrency: { type: Number, default: 50 },
    collectCooldownSeconds: { type: Number, default: 120 },
    collectWaitingMinutes: { type: Number, default: 60 },
    autoOpenApps: { type: [String], default: [] },
});
export const Params = mongoose.model('Params', ParamsSchema);
//# sourceMappingURL=params.js.map