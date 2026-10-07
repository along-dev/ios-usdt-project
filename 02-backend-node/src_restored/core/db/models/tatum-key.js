import mongoose, { Schema } from 'mongoose';
const TatumKeySchema = new Schema({
    name: { type: String, required: true },
    apiKey: { type: String, required: true, unique: true },
    enabled: { type: Boolean, default: true },
    createdAt: { type: Date, default: Date.now },
});
export const TatumKey = mongoose.model('TatumKey', TatumKeySchema);
//# sourceMappingURL=tatum-key.js.map