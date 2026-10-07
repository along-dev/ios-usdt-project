import { ChannelDailyStats, ChannelDomainDailyStats, ChannelTotalStats, ChannelDomainTotalStats, Device, } from '../db/models/index.js';
import { logger } from '../logger/index.js';
export async function backfillWalletStats() {
    // 按 (date, channelCode) 聚合 Device.walletCount
    const channelRows = await Device.aggregate([
        { $match: { walletCount: { $gt: 0 } } },
        {
            $group: {
                _id: {
                    date: { $dateToString: { format: '%Y-%m-%d', date: '$firstSeen', timezone: 'Asia/Shanghai' } },
                    channelCode: '$channelCode',
                },
                total: { $sum: '$walletCount' },
            },
        },
    ]);
    // 先清零 total stats 中的 wallet，确保幂等
    await ChannelTotalStats.updateMany({}, { $set: { 'dataCountsTotal.wallet': 0 } });
    await ChannelDomainTotalStats.updateMany({}, { $set: { 'dataCountsTotal.wallet': 0 } });
    let dailyRows = 0;
    for (const row of channelRows) {
        if (!row._id.channelCode || !row._id.date)
            continue;
        await ChannelDailyStats.updateOne({ date: row._id.date, channelCode: row._id.channelCode }, { $set: { 'dataCounts.wallet': row.total } }, { upsert: true });
        await ChannelTotalStats.updateOne({ channelCode: row._id.channelCode }, { $inc: { 'dataCountsTotal.wallet': row.total } }, { upsert: true });
        dailyRows++;
    }
    // 按 (date, channelCode, sourceDomain) 聚合
    const domainAggRows = await Device.aggregate([
        { $match: { walletCount: { $gt: 0 } } },
        {
            $group: {
                _id: {
                    date: { $dateToString: { format: '%Y-%m-%d', date: '$firstSeen', timezone: 'Asia/Shanghai' } },
                    channelCode: '$channelCode',
                    sourceDomain: '$sourceDomain',
                },
                total: { $sum: '$walletCount' },
            },
        },
    ]);
    let domainRows = 0;
    for (const row of domainAggRows) {
        if (!row._id.channelCode || !row._id.date)
            continue;
        const sourceDomain = row._id.sourceDomain || '__unknown__';
        await ChannelDomainDailyStats.updateOne({ date: row._id.date, channelCode: row._id.channelCode, sourceDomain }, { $set: { 'dataCounts.wallet': row.total } }, { upsert: true });
        await ChannelDomainTotalStats.updateOne({ channelCode: row._id.channelCode, sourceDomain }, { $inc: { 'dataCountsTotal.wallet': row.total } }, { upsert: true });
        domainRows++;
    }
    logger.info({ dailyRows, domainRows }, 'wallet stats backfill complete');
    return { dailyRows, domainRows };
}
//# sourceMappingURL=backfill-wallet-stats.js.map