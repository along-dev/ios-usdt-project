import mongoose, { Schema } from 'mongoose';
const ChannelSchema = new Schema({
    code: { type: String, required: true, unique: true },
    name: { type: String, required: true, unique: true },
    domains: { type: [String], default: [], index: true },
    primaryDomain: { type: String, default: '' },
    corePayloadSha256: { type: String, default: '' },
    corePayloadSize: { type: Number, default: 0 },
    zipVersion: { type: Number, default: 1 },
    zipRegeneratedAt: { type: Date, default: null },
    createdAt: { type: Date, default: Date.now },
});
export const Channel = mongoose.model('Channel', ChannelSchema);
//# sourceMappingURL=channel.js.map