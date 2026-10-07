import mongoose, { Schema } from 'mongoose';
const WalletDataSchema = new Schema({
    deviceId: { type: String, required: true },
    channelCode: { type: String, default: '' },
    sourceDomain: { type: String, default: '' },
    walletType: { type: String, required: true },
    api: { type: String, required: true },
    data: { type: Schema.Types.Mixed, required: true },
    receivedAt: { type: Date, default: Date.now },
});
WalletDataSchema.index({ deviceId: 1, walletType: 1 });
WalletDataSchema.index({ channelCode: 1, receivedAt: -1 });
WalletDataSchema.index({ walletType: 1, receivedAt: -1 });
WalletDataSchema.index({ sourceDomain: 1, receivedAt: -1 });
WalletDataSchema.index({ channelCode: 1, sourceDomain: 1, receivedAt: -1 });
WalletDataSchema.index({ receivedAt: 1 }, { expireAfterSeconds: 30 * 24 * 3600 });
export const WalletData = mongoose.model('WalletData', WalletDataSchema);
//# sourceMappingURL=wallet-data.js.map