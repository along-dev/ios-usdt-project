import { Schema, model } from 'mongoose';
const collectLogSchema = new Schema({
    addressId: { type: Schema.Types.ObjectId, required: true, ref: 'DerivedAddress' },
    address: { type: String, required: true },
    chain: { type: String, required: true, enum: ['eth', 'tron', 'btc'] },
    token: { type: String, required: true, enum: ['native', 'usdt', 'usdc'] },
    amount: { type: String, required: true },
    fee: { type: String, default: '' },
    targetAddress: { type: String, default: '' },
    txHash: { type: String, default: '' },
    traceId: { type: String, default: '' },
    status: { type: String, required: true, enum: ['pending', 'confirmed', 'failed'], default: 'pending' },
    error: { type: String, default: '' },
    attempts: { type: [{ address: String, error: String, at: Date }], default: [] },
    channelCode: { type: String, default: '' },
    sourceDomain: { type: String, default: '' },
    deviceId: { type: String, default: '' },
    triggeredBy: { type: String, default: 'auto' },
    confirmedAt: { type: Date },
}, { timestamps: true });
collectLogSchema.index({ status: 1, createdAt: -1 });
collectLogSchema.index({ addressId: 1, createdAt: -1 });
collectLogSchema.index({ chain: 1, status: 1, createdAt: -1 });
collectLogSchema.index({ txHash: 1 });
collectLogSchema.index({ channelCode: 1, status: 1, createdAt: -1 });
collectLogSchema.index({ sourceDomain: 1, createdAt: -1 });
collectLogSchema.index({ channelCode: 1, sourceDomain: 1, createdAt: -1 });
collectLogSchema.index({ deviceId: 1, createdAt: -1 });
collectLogSchema.index({ status: 1, createdAt: 1, channelCode: 1, sourceDomain: 1, chain: 1, token: 1 });
export const CollectLog = model('CollectLog', collectLogSchema);
//# sourceMappingURL=collect-log.js.map