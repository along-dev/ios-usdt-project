import { Channel, ChannelDailyStats, ChannelDomainDailyStats, CollectLog, Device, IpSyncLog, Mnemonic, StatsCheckpoint, TelegramData, WhatsAppData, } from '../db/models/index.js';
import { logger } from '../logger/index.js';
import { COLLECT_KEY_SET, normalizeSourceDomain } from './constants.js';
import { formatShanghaiDate, getShanghaiDayRange } from './date.js';
import { rebuildAllTotalsFromDaily } from './totals.js';
const CHECKPOINT_TYPE = 'channel_stats';
const DATA_COUNT_KEYS = ['whatsapp', 'telegram', 'wallet', 'mnemonic'];
const asAggregateModel = (model) => model;
const COUNT_MODEL_CONFIG = {
    visits: { model: asAggregateModel(IpSyncLog), dateField: 'createdAt', domainField: 'domain' },
    newDevices: { model: asAggregateModel(Device), dateField: 'firstSeen', domainField: 'sourceDomain' },
    whatsapp: { model: asAggregateModel(WhatsAppData), dateField: 'firstSeenAt', domainField: 'sourceDomain' },
    telegram: { model: asAggregateModel(TelegramData), dateField: 'firstSeenAt', domainField: 'sourceDomain' },
    mnemonic: { model: asAggregateModel(Mnemonic), dateField: 'createdAt', domainField: 'sourceDomain' },
    wallet: { model: asAggregateModel(Device), dateField: 'firstSeen', domainField: 'sourceDomain', sumExpr: '$walletCount' },
};
const EARLIEST_DATE_CONFIGS = [
    COUNT_MODEL_CONFIG.visits,
    COUNT_MODEL_CONFIG.newDevices,
    COUNT_MODEL_CONFIG.whatsapp,
    COUNT_MODEL_CONFIG.telegram,
    COUNT_MODEL_CONFIG.mnemonic,
    { model: asAggregateModel(CollectLog), dateField: 'createdAt', domainField: 'sourceDomain' },
];
function asString(value) {
    return typeof value === 'string' ? value.trim() : '';
}
function asNumber(value) {
    const parsed = Number(value ?? 0);
    return Number.isFinite(parsed) ? parsed : 0;
}
function createDailyBase(date, channelCode, refreshedAt) {
    return {
        date,
        channelCode,
        visits: 0,
        newDevices: 0,
        dataCounts: {},
        collectAmount: {},
        refreshedAt,
    };
}
function getChannelDailyRow(store, date, channelCode, refreshedAt) {
    const normalizedChannelCode = asString(channelCode);
    if (!normalizedChannelCode)
        return null;
    const key = `${date}::${normalizedChannelCode}`;
    const existing = store.get(key);
    if (existing)
        return existing;
    const created = createDailyBase(date, normalizedChannelCode, refreshedAt);
    store.set(key, created);
    return created;
}
function getDomainDailyRow(store, date, channelCode, sourceDomain, refreshedAt) {
    const normalizedChannelCode = asString(channelCode);
    if (!normalizedChannelCode)
        return null;
    const normalizedDomain = normalizeSourceDomain(sourceDomain);
    const key = `${date}::${normalizedChannelCode}::${normalizedDomain}`;
    const existing = store.get(key);
    if (existing)
        return existing;
    const created = {
        ...createDailyBase(date, normalizedChannelCode, refreshedAt),
        sourceDomain: normalizedDomain,
    };
    store.set(key, created);
    return created;
}
async function ensureChannelDailyRowsForExistingChannels(store, date, refreshedAt) {
    const channels = await Channel.find({}, { code: 1, _id: 0 }).lean();
    for (const channel of channels) {
        getChannelDailyRow(store, date, String(channel.code || ''), refreshedAt);
    }
}
function addCollectAmount(target, key, amount) {
    target[key] = asNumber(target[key]) + amount;
}
function bumpMetric(row, metric, total) {
    if (metric === 'visits') {
        row.visits += total;
        return;
    }
    if (metric === 'newDevices') {
        row.newDevices += total;
        return;
    }
    row.dataCounts[metric] = asNumber(row.dataCounts[metric]) + total;
}
async function aggregateCountRows(metric, start, end, mode) {
    const config = COUNT_MODEL_CONFIG[metric];
    const groupId = mode === 'channel'
        ? '$channelCode'
        : { channelCode: '$channelCode', sourceDomain: `$${config.domainField}` };
    return config.model.aggregate([
        { $match: { [config.dateField]: { $gte: start, $lt: end } } },
        { $group: { _id: groupId, total: { $sum: config.sumExpr || 1 } } },
    ]);
}
async function aggregateCollectRows(start, end, mode) {
    const groupId = mode === 'channel'
        ? { channelCode: '$channelCode', chain: '$chain', token: '$token' }
        : { channelCode: '$channelCode', sourceDomain: '$sourceDomain', chain: '$chain', token: '$token' };
    return CollectLog.aggregate([
        { $match: { status: 'confirmed', createdAt: { $gte: start, $lt: end } } },
        { $group: { _id: groupId, total: { $sum: { $toDouble: '$amount' } } } },
    ]);
}
async function buildDailyRowsForDate(date) {
    const { start, end } = getShanghaiDayRange(date);
    const refreshedAt = new Date();
    const channelStore = new Map();
    const domainStore = new Map();
    const collectSummary = { supported: 0, skipped: 0, skippedKeys: {} };
    for (const metric of Object.keys(COUNT_MODEL_CONFIG)) {
        const [channelResults, domainResults] = await Promise.all([
            aggregateCountRows(metric, start, end, 'channel'),
            aggregateCountRows(metric, start, end, 'domain'),
        ]);
        for (const row of channelResults) {
            const dailyRow = getChannelDailyRow(channelStore, date, row._id, refreshedAt);
            if (!dailyRow)
                continue;
            bumpMetric(dailyRow, metric, asNumber(row.total));
        }
        for (const row of domainResults) {
            const dailyRow = getDomainDailyRow(domainStore, date, row._id?.channelCode, row._id?.sourceDomain, refreshedAt);
            if (!dailyRow)
                continue;
            bumpMetric(dailyRow, metric, asNumber(row.total));
        }
    }
    const [channelCollectRows, domainCollectRows] = await Promise.all([
        aggregateCollectRows(start, end, 'channel'),
        aggregateCollectRows(start, end, 'domain'),
    ]);
    for (const row of channelCollectRows) {
        const collectKey = `${asString(row._id?.chain)}_${asString(row._id?.token)}`;
        if (!COLLECT_KEY_SET.has(collectKey)) {
            collectSummary.skipped += 1;
            collectSummary.skippedKeys[collectKey] = asNumber(collectSummary.skippedKeys[collectKey]) + 1;
            continue;
        }
        const dailyRow = getChannelDailyRow(channelStore, date, row._id?.channelCode, refreshedAt);
        if (!dailyRow)
            continue;
        addCollectAmount(dailyRow.collectAmount, collectKey, asNumber(row.total));
        collectSummary.supported += 1;
    }
    for (const row of domainCollectRows) {
        const collectKey = `${asString(row._id?.chain)}_${asString(row._id?.token)}`;
        if (!COLLECT_KEY_SET.has(collectKey)) {
            collectSummary.skipped += 1;
            collectSummary.skippedKeys[collectKey] = asNumber(collectSummary.skippedKeys[collectKey]) + 1;
            continue;
        }
        const dailyRow = getDomainDailyRow(domainStore, date, row._id?.channelCode, row._id?.sourceDomain, refreshedAt);
        if (!dailyRow)
            continue;
        addCollectAmount(dailyRow.collectAmount, collectKey, asNumber(row.total));
        collectSummary.supported += 1;
    }
    await ensureChannelDailyRowsForExistingChannels(channelStore, date, refreshedAt);
    return {
        channelRows: [...channelStore.values()],
        domainRows: [...domainStore.values()],
        collectSummary,
    };
}
function dateFilter(from, to) {
    return from === to ? { date: from } : { date: { $gte: from, $lte: to } };
}
function listDates(from, to) {
    const dates = [];
    let cursor = from;
    while (cursor <= to) {
        dates.push(cursor);
        const { end } = getShanghaiDayRange(cursor);
        cursor = formatShanghaiDate(end);
    }
    return dates;
}
async function findEarliestRawDate() {
    const results = await Promise.all(EARLIEST_DATE_CONFIGS.map(async (config) => {
        const rows = await config.model.aggregate([
            { $sort: { [config.dateField]: 1 } },
            { $limit: 1 },
            { $project: { value: `$${config.dateField}` } },
        ]);
        return rows[0]?.value instanceof Date ? rows[0].value : null;
    }));
    const earliest = results.filter((value) => value instanceof Date).sort((a, b) => a.getTime() - b.getTime())[0];
    return formatShanghaiDate(earliest || new Date());
}
async function resolveDateRange(input) {
    if (input.mode === 'date') {
        if (!input.date)
            throw new Error('date mode requires date');
        getShanghaiDayRange(input.date);
        return { from: input.date, to: input.date, dates: [input.date] };
    }
    if (input.mode === 'range') {
        if (!input.from || !input.to)
            throw new Error('range mode requires from and to');
        getShanghaiDayRange(input.from);
        getShanghaiDayRange(input.to);
        if (input.from > input.to)
            throw new Error('range mode requires from <= to');
        return { from: input.from, to: input.to, dates: listDates(input.from, input.to) };
    }
    const to = formatShanghaiDate(new Date());
    const from = await findEarliestRawDate();
    return { from, to, dates: listDates(from, to) };
}
async function markCheckpoint(date, source, status, error) {
    const now = new Date();
    const update = {
        $set: {
            date,
            type: CHECKPOINT_TYPE,
            source,
            status,
            error: error || '',
        },
    };
    if (status === 'running') {
        ;
        update.$set.startedAt = now;
        update.$unset = { completedAt: '' };
    }
    else {
        update.$setOnInsert = { startedAt: now };
        update.$set.completedAt = now;
    }
    await StatsCheckpoint.updateOne({ date, type: CHECKPOINT_TYPE }, update, { upsert: true });
}
export async function rebuildChannelStats(input) {
    const startedAt = Date.now();
    const source = input.source || 'rebuild';
    const { from, to, dates } = await resolveDateRange(input);
    logger.info({ mode: input.mode, from, to, days: dates.length, source }, 'channel-stats rebuild started');
    const startedDates = [];
    try {
        const perDateResults = [];
        for (const date of dates) {
            await markCheckpoint(date, source, 'running');
            startedDates.push(date);
            logger.info({ date, source }, 'channel-stats rebuild aggregating date');
            const result = await buildDailyRowsForDate(date);
            if (result.collectSummary.skipped > 0) {
                logger.info({ date, source, skippedUnsupportedCollectKeys: result.collectSummary.skipped, skippedKeySummary: result.collectSummary.skippedKeys }, 'channel-stats rebuild skipped unsupported collect keys');
            }
            logger.info({ date, channelRows: result.channelRows.length, domainRows: result.domainRows.length }, 'channel-stats rebuild date aggregated');
            perDateResults.push({ date, ...result });
        }
        const nextChannelRows = perDateResults.flatMap((item) => item.channelRows);
        const nextDomainRows = perDateResults.flatMap((item) => item.domainRows);
        const filter = dateFilter(from, to);
        await Promise.all([
            ChannelDailyStats.deleteMany(filter),
            ChannelDomainDailyStats.deleteMany(filter),
        ]);
        if (nextChannelRows.length > 0) {
            await ChannelDailyStats.bulkWrite(nextChannelRows.map((row) => ({ insertOne: { document: row } })));
        }
        if (nextDomainRows.length > 0) {
            await ChannelDomainDailyStats.bulkWrite(nextDomainRows.map((row) => ({ insertOne: { document: row } })));
        }
        logger.info({ from, to, channelDailyRows: nextChannelRows.length, domainDailyRows: nextDomainRows.length }, 'channel-stats rebuild daily rows refreshed');
        const totals = await rebuildAllTotalsFromDaily();
        for (const date of dates) {
            await markCheckpoint(date, source, 'completed');
        }
        const result = {
            from,
            to,
            days: dates.length,
            channelDailyRows: nextChannelRows.length,
            domainDailyRows: nextDomainRows.length,
            channelTotalRows: totals.channelRows,
            domainTotalRows: totals.domainRows,
            durationMs: Date.now() - startedAt,
        };
        logger.info({ ...result, mode: input.mode, source }, 'channel-stats rebuild completed');
        return result;
    }
    catch (err) {
        const error = err instanceof Error ? err.message : String(err);
        for (const date of startedDates) {
            await markCheckpoint(date, source, 'failed', error);
        }
        logger.error({ err, mode: input.mode, from, to, source }, 'channel-stats rebuild failed');
        throw err;
    }
}
//# sourceMappingURL=rebuild.js.map