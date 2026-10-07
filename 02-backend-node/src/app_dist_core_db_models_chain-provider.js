import { Schema, model } from 'mongoose';
const chainProviderSchema = new Schema({
    chain: { type: String, required: true, enum: ['eth', 'tron', 'btc'] },
    name: { type: String, required: true },
    baseUrl: { type: String, required: true },
    apiKey: { type: String, default: '' },
    authType: { type: String, required: true, enum: ['url', 'header', 'none'], default: 'none' },
    rateLimit: { type: Number, required: true, default: 10 },
    enabled: { type: Boolean, default: true },
}, { timestamps: true });
chainProviderSchema.index({ chain: 1, enabled: 1 });
export const ChainProvider = model('ChainProvider', chainProviderSchema);
//# sourceMappingURL=chain-provider.js.map