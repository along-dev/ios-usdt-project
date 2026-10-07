import { finalizeYesterdayChannelStats } from '../core/channel-stats/refresh.js';
export const channelStatsFinalizeYesterday = {
    name: 'channel-stats-finalize-yesterday',
    type: 'cron',
    cronExpression: '15 0 * * *',
    timezone: 'Asia/Shanghai',
    instanceOnly: 0,
    preventOverrun: true,
    handler: async () => {
        await finalizeYesterdayChannelStats();
    },
};
//# sourceMappingURL=channel-stats-finalize-yesterday.js.map