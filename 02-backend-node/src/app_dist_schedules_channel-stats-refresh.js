import { refreshTodayChannelStats } from '../core/channel-stats/refresh.js';
export const channelStatsRefresh = {
    name: 'channel-stats-refresh',
    type: 'cron',
    cronExpression: '*/10 * * * *',
    timezone: 'Asia/Shanghai',
    instanceOnly: 0,
    preventOverrun: true,
    handler: async () => {
        await refreshTodayChannelStats();
    },
};
//# sourceMappingURL=channel-stats-refresh.js.map