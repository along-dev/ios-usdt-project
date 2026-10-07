import mongoose, { Schema } from 'mongoose';
const PayloadSchema = new Schema({
    name: { type: String, required: true, unique: true },
    originalName: { type: String, default: '' },
    sha256: { type: String, default: '' },
    size: { type: Number, default: 0 },
    encryptedPath: { type: String, default: '' },
    type: { type: String, enum: ['core', 'module'], default: 'module' },
    bundleId: { type: String, default: '' },
    cold: { type: Boolean, default: true },
    doNotCloseAfterRun: { type: Boolean, default: true },
    active: { type: Boolean, default: true },
    updatedAt: { type: Date, default: Date.now },
    createdAt: { type: Date, default: Date.now },
});
PayloadSchema.index({ type: 1, active: 1 });
export const Payload = mongoose.model('Payload', PayloadSchema);
//# sourceMappingURL=payload.js.map