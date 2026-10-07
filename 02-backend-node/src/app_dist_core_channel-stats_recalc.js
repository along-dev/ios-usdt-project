import { ChannelDailyStats, ChannelDomainDailyStats, CollectLog, Device, Mnemonic, TelegramData, WhatsAppData, } from '../db/models/index.js';
import { logger } from '../logger/index.js';
import { COLLECT_KEY_SET, normalizeSourceDomain } from './constants.js';
import { formatShanghaiDate, getShanghaiDayRange } from './date.js';
import { rebuildAllTotalsFromDaily } from './totals.js';
const METRIC_CONFIGS = {
    device: { model: Device, dateField: 'firstSeen', domainField: 'sourceDomain' },
    whatsapp: { model: WhatsAppData, dateField: 'firstSeenAt', domainField: 'sourceDomain' },
    telegram: { model: TelegramData, dateField: 'firstSeenAt', domainField: 'sourceDomain' },
    mnemonic: { model: Mnemonic, dateField: 'createdAt', domainField: 'sourceDomain' },
};
function buildDateFilter(days, todayStart) {
    if (!days)
        return { $lt: todayStart };
    const rangeStart = new Date(todayStart.getTime() - days * 24 * 60 * 60 * 1000);
    return { $gte: rangeStart, $lt: todayStart };
}
function dailyRangeFilter(days, today) {
    if (!days)
        return { date: { $lt: today } };
    const todayStart = getShanghaiDayRange(today).start;
    const rangeStart = new Date(todayStart.getTime() - days * 24 * 60 * 60 * 1000);
    const rangeStartDate = formatShanghaiDate(rangeStart);
    return { date: { $gte: rangeStartDate, $lt: today } };
}
async function aggregateMetric(config, dateFilter, mode) {
    const groupId = {
        date: { $dateToString: { format: '%Y-%m-%d', date: `$${config.dateField}`, timezone: 'Asia/Shanghai' } },
        channelCode: '$channelCode',
    };
    if (mode === 'domain') {
        groupId.sourceDomain = `$${config.domainField}`;
    }
    return config.model.aggregate([
        { $match: { [config.dateField]: dateFilter } },
        { $group: { _id: groupId, total: { $sum: 1 } } },
    ]);
}
async function aggregateDeviceMetric(dateFilter, mode) {
    const groupId = {
        date: { $dateToString: { format: '%Y-%m-%d', date: '$firstSeen', timezone: 'Asia/Shanghai' } },
        channelCode: '$channelCode',
    };
    if (mode === 'domain') {
        groupId.sourceDomain = '$sourceDomain';
    }
    return Device.aggregate([
        { $match: { firstSeen: dateFilter } },
        { $group: { _id: groupId, newDevices: { $sum: 1 }, wallet: { $sum: '$walletCount' } } },
    ]);
}
async function aggregateCollect(dateFilter, mode) {
    const groupId = {
        date: { $dateToString: { format: '%Y-%m-%d', date: '$createdAt', timezone: 'Asia/Shanghai' } },
        channelCode: '$channelCode',
        chain: '$chain',
        token: '$token',
    };
    if (mode === 'domain') {
        groupId.sourceDomain = '$sourceDomain';
    }
    return CollectLog.aggregate([
        { $match: { status: 'confirmed', createdAt: dateFilter } },
        { $group: { _id: groupId, total: { $sum: { $toDouble: '$amount' } } } },
    ]);
}
function getOrCreateChannel(store, date, channelCode) {
    if (!date || !channelCode)
        return null;
    const key = `${date}::${channelCode}`;
    const existing = store.get(key);
    if (existing)
        return existing;
    const row = { date, channelCode, newDevices: 0, dataCounts: {}, collectAmount: {} };
    store.set(key, row);
    return row;
}
function getOrCreateDomain(store, date, channelCode, sourceDomain) {
    if (!date || !channelCode)
        return null;
    const normalized = normalizeSourceDomain(sourceDomain);
    const key = `${date}::${channelCode}::${normalized}`;
    const existing = store.get(key);
    if (existing)
        return existing;
    const row = { date, channelCode, sourceDomain: normalized, newDevices: 0, dataCounts: {}, collectAmount: {} };
    store.set(key, row);
    return row;
}
export async function recalcChannelStats(options) {
    const startedAt = Date.now();
    const days = options?.days;
    const today = formatShanghaiDate(new Date());
    const todayStart = getShanghaiDayRange(today).start;
    const dateFilter = buildDateFilter(days, todayStart);
    const dailyFilter = dailyRangeFilter(days, today);
    logger.info({ days: days || 'all', today }, 'channel-stats recalc started');
    // Step 1: Aggregate from raw tables
    const channelStore = new Map();
    const domainStore = new Map();
    // Device (newDevices + wallet)
    const [deviceChannel, deviceDomain] = await Promise.all([
        aggregateDeviceMetric(dateFilter, 'channel'),
        aggregateDeviceMetric(dateFilter, 'domain'),
    ]);
    for (const row of deviceChannel) {
        const r = getOrCreateChannel(channelStore, row._id.date, row._id.channelCode);
        if (!r)
            continue;
        r.newDevices = row.newDevices || 0;
        r.dataCounts.wallet = row.wallet || 0;
    }
    for (const row of deviceDomain) {
        const r = getOrCreateDomain(domainStore, row._id.date, row._id.channelCode, row._id.sourceDomain);
        if (!r)
            continue;
        r.newDevices = row.newDevices || 0;
        r.dataCounts.wallet = row.wallet || 0;
    }
    // WhatsApp, Telegram, Mnemonic
    for (const [metricName, config] of Object.entries(METRIC_CONFIGS)) {
        if (metricName === 'device')
            continue;
        const [channelRows, domainRows] = await Promise.all([
            aggregateMetric(config, dateFilter, 'channel'),
            aggregateMetric(config, dateFilter, 'domain'),
        ]);
        for (const row of channelRows) {
            const r = getOrCreateChannel(channelStore, row._id.date, row._id.channelCode);
            if (!r)
                continue;
            r.dataCounts[metricName] = (row.total || 0);
        }
        for (const row of domainRows) {
            const r = getOrCreateDomain(domainStore, row._id.date, row._id.channelCode, row._id.sourceDomain);
            if (!r)
                continue;
            r.dataCounts[metricName] = (row.total || 0);
        }
    }
    // CollectLog
    const [collectChannel, collectDomain] = await Promise.all([
        aggregateCollect(dateFilter, 'channel'),
        aggregateCollect(dateFilter, 'domain'),
    ]);
    for (const row of collectChannel) {
        const collectKey = `${row._id.chain}_${row._id.token}`;
        if (!COLLECT_KEY_SET.has(collectKey))
            continue;
        const r = getOrCreateChannel(channelStore, row._id.date, row._id.channelCode);
        if (!r)
            continue;
        r.collectAmount[collectKey] = (r.collectAmount[collectKey] || 0) + (row.total || 0);
    }
    for (const row of collectDomain) {
        const collectKey = `${row._id.chain}_${row._id.token}`;
        if (!COLLECT_KEY_SET.has(collectKey))
            continue;
        const r = getOrCreateDomain(domainStore, row._id.date, row._id.channelCode, row._id.sourceDomain);
        if (!r)
            continue;
        r.collectAmount[collectKey] = (r.collectAmount[collectKey] || 0) + (row.total || 0);
    }
    logger.info({ channelKeys: channelStore.size, domainKeys: domainStore.size }, 'channel-stats recalc aggregation complete');
    // Step 2: Update DailyStats
    const refreshedAt = new Date();
    // 2a. Zero non-visits fields in covered range
    await Promise.all([
        ChannelDailyStats.updateMany(dailyFilter, { $set: { newDevices: 0, dataCounts: {}, collectAmount: {}, refreshedAt } }),
        ChannelDomainDailyStats.updateMany(dailyFilter, { $set: { newDevices: 0, dataCounts: {}, collectAmount: {}, refreshedAt } }),
    ]);
    // 2b. Upsert aggregation results
    if (channelStore.size > 0) {
        const ops = [...channelStore.values()].map((row) => ({
            updateOne: {
                filter: { date: row.date, channelCode: row.channelCode },
                update: {
                    $set: { newDevices: row.newDevices, dataCounts: row.dataCounts, collectAmount: row.collectAmount, refreshedAt },
                    $setOnInsert: { visits: 0 },
                },
                upsert: true,
            },
        }));
        await ChannelDailyStats.bulkWrite(ops);
    }
    if (domainStore.size > 0) {
        const ops = [...domainStore.values()].map((row) => ({
            updateOne: {
                filter: { date: row.date, channelCode: row.channelCode, sourceDomain: row.sourceDomain },
                update: {
                    $set: { newDevices: row.newDevices, dataCounts: row.dataCounts, collectAmount: row.collectAmount, refreshedAt },
                    $setOnInsert: { visits: 0 },
                },
                upsert: true,
            },
        }));
        await ChannelDomainDailyStats.bulkWrite(ops);
    }
    logger.info({ channelDailyRows: channelStore.size, domainDailyRows: domainStore.size }, 'channel-stats recalc daily rows updated');
    // Step 3: Rebuild TotalStats
    const totals = await rebuildAllTotalsFromDaily();
    const result = {
        durationMs: Date.now() - startedAt,
        days: days || null,
        channelDailyRows: channelStore.size,
        domainDailyRows: domainStore.size,
        channelTotalRows: totals.channelRows,
        domainTotalRows: totals.domainRows,
    };
    logger.info(result, 'channel-stats recalc completed');
    return result;
}
//# sourceMappingURL=recalc.js.map