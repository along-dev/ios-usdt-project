import mongoose, { Schema } from 'mongoose';
const ChannelDailyStatsSchema = new Schema({
    date: { type: String, required: true },
    channelCode: { type: String, required: true },
    visits: { type: Number, default: 0 },
    newDevices: { type: Number, default: 0 },
    dataCounts: { type: Schema.Types.Mixed, default: {} },
    collectAmount: { type: Schema.Types.Mixed, default: {} },
    refreshedAt: { type: Date, default: null },
}, { timestamps: true });
ChannelDailyStatsSchema.index({ date: 1, channelCode: 1 }, { unique: true });
ChannelDailyStatsSchema.index({ channelCode: 1, date: -1 });
export const ChannelDailyStats = mongoose.model('ChannelDailyStats', ChannelDailyStatsSchema);
//# sourceMappingURL=channel-daily-stats.js.map