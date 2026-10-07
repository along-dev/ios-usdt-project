import { Schema, model } from 'mongoose';
const collectConfigSchema = new Schema({
    channelCode: { type: String, default: null },
    chain: { type: String, required: true, enum: ['eth', 'tron', 'btc'] },
    token: { type: String, required: true, enum: ['native', 'usdt', 'usdc'] },
    threshold: { type: String, required: true, default: '0' },
    enabled: { type: Boolean, default: false },
}, { timestamps: true });
collectConfigSchema.index({ chain: 1, token: 1, channelCode: 1 }, { unique: true });
export const CollectConfig = model('CollectConfig', collectConfigSchema);
//# sourceMappingURL=collect-config.js.map