import mongoose, { Schema } from 'mongoose';
const SessionSchema = new Schema({
    refreshToken: { type: String, required: true },
    deviceInfo: { type: String, default: '' },
    ip: { type: String, default: '' },
    lastUsed: { type: Date, default: Date.now },
    createdAt: { type: Date, default: Date.now },
}, { _id: true });
const TotpSchema = new Schema({
    secret: { type: String, required: true },
    enabled: { type: Boolean, default: false },
    verifiedAt: { type: Date },
}, { _id: false });
const UserSchema = new Schema({
    username: { type: String, required: true, unique: true, minlength: 3, maxlength: 10, match: /^[a-zA-Z0-9_]+$/ },
    passwordHash: { type: String, required: true },
    role: { type: String, enum: ['admin', 'channel_admin', 'user'], default: 'user' },
    status: { type: String, enum: ['active', 'disabled'], default: 'active' },
    roleId: { type: Schema.Types.ObjectId, ref: 'Role', default: null },
    channelCodes: { type: [String], default: [] },
    canExportWhatsapp: { type: Boolean, default: false },
    sessions: { type: [SessionSchema], default: [] },
    totp: { type: TotpSchema, default: null },
    createdAt: { type: Date, default: Date.now },
});
UserSchema.index({ roleId: 1 });
export const User = mongoose.model('User', UserSchema);
//# sourceMappingURL=user.js.map