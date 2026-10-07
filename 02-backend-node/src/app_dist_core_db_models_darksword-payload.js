import mongoose, { Schema } from 'mongoose';
const DarkswordPayloadSchema = new Schema({
    name: { type: String, required: true, unique: true },
    sha256: { type: String, default: '' },
    size: { type: Number, default: 0 },
    encryptedPath: { type: String, default: '' },
    active: { type: Boolean, default: true },
    updatedAt: { type: Date, default: Date.now },
    createdAt: { type: Date, default: Date.now },
});
export const DarkswordPayload = mongoose.model('DarkswordPayload', DarkswordPayloadSchema);
//# sourceMappingURL=darksword-payload.js.map