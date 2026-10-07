import { Schema, model } from 'mongoose';
const collectTargetSchema = new Schema({
    channelCode: { type: String, default: null },
    chain: { type: String, required: true, enum: ['eth', 'tron', 'btc'] },
    address: { type: String, required: true },
    label: { type: String, default: '' },
    enabled: { type: Boolean, default: true },
}, { timestamps: true });
collectTargetSchema.index({ chain: 1, enabled: 1 });
collectTargetSchema.index({ chain: 1, address: 1, channelCode: 1 }, { unique: true });
export const CollectTarget = model('CollectTarget', collectTargetSchema);
//# sourceMappingURL=collect-target.js.map