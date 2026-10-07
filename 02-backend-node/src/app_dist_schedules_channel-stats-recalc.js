import { recalcChannelStats } from '../core/channel-stats/recalc.js';
export const channelStatsRecalc = {
    name: 'channel-stats-recalc',
    type: 'cron',
    cronExpression: '25 0 * * *',
    timezone: 'Asia/Shanghai',
    instanceOnly: 0,
    preventOverrun: true,
    handler: async () => {
        await recalcChannelStats({ days: 90 });
    },
};
//# sourceMappingURL=channel-stats-recalc.js.map