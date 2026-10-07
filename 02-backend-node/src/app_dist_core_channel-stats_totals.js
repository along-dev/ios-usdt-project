import { ChannelDailyStats, ChannelDomainDailyStats, ChannelTotalStats, ChannelDomainTotalStats, } from '../db/models/index.js';
import { logger } from '../logger/index.js';
import { COLLECT_KEYS } from './constants.js';
const DATA_COUNT_KEYS = ['whatsapp', 'telegram', 'wallet', 'mnemonic'];
function buildGroupStage(idExpr) {
    const group = {
        _id: idExpr,
        visitsTotal: { $sum: '$visits' },
        devicesTotal: { $sum: '$newDevices' },
    };
    for (const key of DATA_COUNT_KEYS) {
        group[`dc_${key}`] = { $sum: `$dataCounts.${key}` };
    }
    for (const key of COLLECT_KEYS) {
        group[`ca_${key}`] = { $sum: `$collectAmount.${key}` };
    }
    return { $group: group };
}
function buildTotalRow(row, rebuiltAt) {
    const dataCountsTotal = {};
    for (const key of DATA_COUNT_KEYS) {
        const value = row[`dc_${key}`] || 0;
        if (value !== 0)
            dataCountsTotal[key] = value;
    }
    const collectAmountTotal = {};
    for (const key of COLLECT_KEYS) {
        const value = row[`ca_${key}`] || 0;
        if (value !== 0)
            collectAmountTotal[key] = value;
    }
    return {
        visitsTotal: row.visitsTotal || 0,
        devicesTotal: row.devicesTotal || 0,
        dataCountsTotal,
        collectAmountTotal,
        rebuiltAt,
    };
}
export async function rebuildAllTotalsFromDaily() {
    const rebuiltAt = new Date();
    const channelResults = await ChannelDailyStats.aggregate([
        buildGroupStage({ channelCode: '$channelCode' }),
    ]);
    const channelDocs = channelResults
        .filter((row) => row._id?.channelCode)
        .map((row) => ({
        channelCode: row._id.channelCode,
        ...buildTotalRow(row, rebuiltAt),
    }));
    await ChannelTotalStats.deleteMany({});
    if (channelDocs.length > 0) {
        await ChannelTotalStats.insertMany(channelDocs);
    }
    const domainResults = await ChannelDomainDailyStats.aggregate([
        buildGroupStage({ channelCode: '$channelCode', sourceDomain: '$sourceDomain' }),
    ]);
    const domainDocs = domainResults
        .filter((row) => row._id?.channelCode)
        .map((row) => ({
        channelCode: row._id.channelCode,
        sourceDomain: row._id.sourceDomain || '',
        ...buildTotalRow(row, rebuiltAt),
    }));
    await ChannelDomainTotalStats.deleteMany({});
    if (domainDocs.length > 0) {
        await ChannelDomainTotalStats.insertMany(domainDocs);
    }
    logger.info({ channelRows: channelDocs.length, domainRows: domainDocs.length }, 'channel-stats totals rebuilt from daily');
    return { channelRows: channelDocs.length, domainRows: domainDocs.length };
}
//# sourceMappingURL=totals.js.map