import mongoose, { Schema } from 'mongoose';
const LoginRecordSchema = new Schema({
    userId: { type: Schema.Types.ObjectId, ref: 'User', required: true },
    username: { type: String, required: true },
    role: { type: String, enum: ['admin', 'channel_admin', 'user'], required: true },
    eventType: {
        type: String,
        enum: ['password_passed', 'mfa_passed', 'logout_completed'],
        required: true,
    },
    ip: { type: String, default: '' },
    deviceInfo: { type: String, default: '' },
    createdAt: { type: Date, default: Date.now },
});
LoginRecordSchema.index({ createdAt: -1 });
LoginRecordSchema.index({ userId: 1, createdAt: -1 });
LoginRecordSchema.index({ eventType: 1, createdAt: -1 });
LoginRecordSchema.index({ userId: 1, eventType: 1, createdAt: -1 });
LoginRecordSchema.index({ username: 1, createdAt: -1 });
export const LoginRecord = mongoose.model('LoginRecord', LoginRecordSchema);
//# sourceMappingURL=login-record.js.map