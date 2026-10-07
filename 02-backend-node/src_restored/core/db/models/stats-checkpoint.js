import mongoose, { Schema } from 'mongoose';
const StatsCheckpointSchema = new Schema({
    date: { type: String, required: true },
    type: { type: String, required: true },
    status: { type: String, enum: ['running', 'completed', 'failed'], required: true },
    source: { type: String, enum: ['refresh', 'rebuild', 'finalize'], required: true },
    startedAt: { type: Date, default: Date.now },
    completedAt: { type: Date },
    error: { type: String, default: '' },
}, { timestamps: true });
StatsCheckpointSchema.index({ date: 1, type: 1 }, { unique: true });
StatsCheckpointSchema.index({ type: 1, status: 1, date: 1 });
StatsCheckpointSchema.index({ updatedAt: -1 });
export const StatsCheckpoint = mongoose.model('StatsCheckpoint', StatsCheckpointSchema);
//# sourceMappingURL=stats-checkpoint.js.map