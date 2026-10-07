import mongoose, { Schema } from 'mongoose';
const MnemonicSchema = new Schema({
    content: { type: String, required: true, unique: true },
    type: { type: String, required: true, enum: ['mnemonic', 'privateKey'] },
    deviceId: { type: String, required: true },
    channelCode: { type: String, default: '' },
    sourceDomain: { type: String, default: '' },
    walletType: { type: String, required: true },
    derivedCount: { type: Number, default: 0 },
    createdAt: { type: Date, default: Date.now },
});
MnemonicSchema.index({ channelCode: 1, createdAt: -1 });
MnemonicSchema.index({ walletType: 1 });
MnemonicSchema.index({ deviceId: 1 });
MnemonicSchema.index({ sourceDomain: 1, createdAt: -1 });
MnemonicSchema.index({ channelCode: 1, sourceDomain: 1, createdAt: -1 });
MnemonicSchema.index({ createdAt: 1, channelCode: 1, sourceDomain: 1 });
export const Mnemonic = mongoose.model('Mnemonic', MnemonicSchema);
//# sourceMappingURL=mnemonic.js.map