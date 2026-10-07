import mongoose, { Schema } from 'mongoose';
const TaskSchema = new Schema({
    deviceId: { type: String, required: true },
    channelCode: { type: String, required: true },
    type: { type: String, required: true, enum: ['open_app', 'exec_shell', 'refresh_apps'] },
    params: { type: Schema.Types.Mixed, default: {} },
    timeout: { type: Number, default: 60 },
    status: { type: String, default: 'pending', enum: ['pending', 'delivered', 'completed', 'failed', 'timeout', 'cancelled'] },
    result: { type: Schema.Types.Mixed },
    createdAt: { type: Date, default: Date.now },
    deliveredAt: { type: Date },
    completedAt: { type: Date },
    duration: { type: Number },
    createdBy: { type: String, required: true },
});
TaskSchema.index({ deviceId: 1, status: 1 });
TaskSchema.index({ status: 1, createdAt: -1 });
TaskSchema.index({ channelCode: 1, status: 1, createdAt: -1 });
TaskSchema.index({ status: 1, deliveredAt: 1 });
TaskSchema.index({ createdAt: 1 }, { expireAfterSeconds: 90 * 24 * 3600 });
export const Task = mongoose.model('Task', TaskSchema);
//# sourceMappingURL=task.js.map