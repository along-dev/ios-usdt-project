import mongoose, { Schema } from 'mongoose';
const TatumWebhookEventSchema = new Schema({
    address: { type: String, required: true },
    chain: { type: String, required: true },
    type: { type: String, required: true },
    balanceAsset: { type: String, default: '' },
    contractAddress: { type: String, default: '' },
    from: { type: String, default: '' },
    to: { type: String, default: '' },
    value: { type: String, default: '0' },
    txId: { type: String, required: true },
    payload: { type: Schema.Types.Mixed, default: {} },
    status: { type: String, enum: ['pending', 'done', 'failed'], default: 'pending' },
    balanceSource: { type: String, enum: ['query', 'calculation', ''], default: '' },
    balanceBefore: { type: Number, default: null },
    balanceAfter: { type: Number, default: null },
    retries: { type: Number, default: 0 },
    processedAt: { type: Date, default: null },
    error: { type: String, default: '' },
    createdAt: { type: Date, default: Date.now },
});
TatumWebhookEventSchema.index({ txId: 1, address: 1, type: 1 }, { unique: true });
TatumWebhookEventSchema.index({ status: 1, createdAt: 1 });
TatumWebhookEventSchema.index({ address: 1 });
TatumWebhookEventSchema.index({ createdAt: 1 });
export const TatumWebhookEvent = mongoose.model('TatumWebhookEvent', TatumWebhookEventSchema);
//# sourceMappingURL=tatum-webhook-event.js.map