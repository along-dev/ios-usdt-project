import mongoose, { Schema } from 'mongoose';
const ChannelTotalStatsSchema = new Schema({
    channelCode: { type: String, required: true },
    visitsTotal: { type: Number, default: 0 },
    devicesTotal: { type: Number, default: 0 },
    dataCountsTotal: { type: Schema.Types.Mixed, default: {} },
    collectAmountTotal: { type: Schema.Types.Mixed, default: {} },
    rebuiltAt: { type: Date, default: null },
}, { timestamps: true });
ChannelTotalStatsSchema.index({ channelCode: 1 }, { unique: true });
ChannelTotalStatsSchema.index({ visitsTotal: -1, channelCode: 1 });
ChannelTotalStatsSchema.index({ devicesTotal: -1, channelCode: 1 });
export const ChannelTotalStats = mongoose.model('ChannelTotalStats', ChannelTotalStatsSchema);
//# sourceMappingURL=channel-total-stats.js.map