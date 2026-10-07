import mongoose, { Schema } from 'mongoose';
const ChannelDomainDailyStatsSchema = new Schema({
    date: { type: String, required: true },
    channelCode: { type: String, required: true },
    sourceDomain: { type: String, required: true },
    visits: { type: Number, default: 0 },
    newDevices: { type: Number, default: 0 },
    dataCounts: { type: Schema.Types.Mixed, default: {} },
    collectAmount: { type: Schema.Types.Mixed, default: {} },
    refreshedAt: { type: Date, default: null },
}, { timestamps: true });
ChannelDomainDailyStatsSchema.index({ date: 1, channelCode: 1, sourceDomain: 1 }, { unique: true });
ChannelDomainDailyStatsSchema.index({ channelCode: 1, date: -1 });
ChannelDomainDailyStatsSchema.index({ channelCode: 1, sourceDomain: 1, date: -1 });
export const ChannelDomainDailyStats = mongoose.model('ChannelDomainDailyStats', ChannelDomainDailyStatsSchema);
//# sourceMappingURL=channel-domain-daily-stats.js.map