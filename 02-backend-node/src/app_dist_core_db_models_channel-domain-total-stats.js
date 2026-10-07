import mongoose, { Schema } from 'mongoose';
const ChannelDomainTotalStatsSchema = new Schema({
    channelCode: { type: String, required: true },
    sourceDomain: { type: String, required: true },
    visitsTotal: { type: Number, default: 0 },
    devicesTotal: { type: Number, default: 0 },
    dataCountsTotal: { type: Schema.Types.Mixed, default: {} },
    collectAmountTotal: { type: Schema.Types.Mixed, default: {} },
    rebuiltAt: { type: Date, default: null },
}, { timestamps: true });
ChannelDomainTotalStatsSchema.index({ channelCode: 1, sourceDomain: 1 }, { unique: true });
ChannelDomainTotalStatsSchema.index({ channelCode: 1, visitsTotal: -1, sourceDomain: 1 });
ChannelDomainTotalStatsSchema.index({ channelCode: 1, devicesTotal: -1, sourceDomain: 1 });
export const ChannelDomainTotalStats = mongoose.model('ChannelDomainTotalStats', ChannelDomainTotalStatsSchema);
//# sourceMappingURL=channel-domain-total-stats.js.map