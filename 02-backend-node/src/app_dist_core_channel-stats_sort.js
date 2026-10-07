import { CHANNEL_STATS_SORT_FIELDS, } from './types.js';
const SORT_FIELD_SET = new Set(CHANNEL_STATS_SORT_FIELDS);
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const DATABASE_SORT_FIELD_SET = new Set([
    'visitsTotal',
    'devicesTotal',
    'dataCounts.whatsapp.total',
    'dataCounts.telegram.total',
    'dataCounts.wallet.total',
    'dataCounts.mnemonic.total',
    'collect.eth_native',
    'collect.eth_usdt',
    'collect.eth_usdc',
    'collect.tron_native',
    'collect.tron_usdt',
    'collect.btc_native',
    'collectAmount.eth_native.total',
    'collectAmount.eth_usdt.total',
    'collectAmount.eth_usdc.total',
    'collectAmount.tron_native.total',
    'collectAmount.tron_usdt.total',
    'collectAmount.btc_native.total',
]);
export function normalizeChannelStatsSortField(sortField) {
    if (!SORT_FIELD_SET.has(sortField))
        return 'visitsTotal';
    return DATABASE_SORT_FIELD_SET.has(sortField)
        ? sortField
        : 'visitsTotal';
}
export function normalizeChannelStatsQuery(query) {
    const pageRaw = Number.parseInt(String(query.page || '1'), 10);
    const pageSizeRaw = Number.parseInt(String(query.pageSize || '10'), 10);
    const sortFieldRaw = String(query.sortField || 'visitsTotal');
    const sortOrderRaw = String(query.sortOrder || 'desc');
    const dateRaw = typeof query.date === 'string' && DATE_RE.test(query.date.trim()) ? query.date.trim() : undefined;
    return {
        date: dateRaw,
        page: Number.isFinite(pageRaw) && pageRaw > 0 ? pageRaw : 1,
        pageSize: Number.isFinite(pageSizeRaw) && pageSizeRaw > 0 && pageSizeRaw <= 100 ? pageSizeRaw : 10,
        sortField: normalizeChannelStatsSortField(sortFieldRaw),
        sortOrder: sortOrderRaw === 'asc' ? 'asc' : 'desc',
    };
}
function readPathValue(source, path) {
    let current = source;
    for (const segment of path) {
        if (current == null)
            return 0;
        if (typeof current !== 'object') {
            const numberValue = Number(current ?? 0);
            return Number.isFinite(numberValue) ? numberValue : 0;
        }
        current = current[segment];
    }
    const value = Number(current ?? 0);
    return Number.isFinite(value) ? value : 0;
}
function readSortValue(row, sortField) {
    if (sortField === 'visitsToday')
        return Number(row.visitsCurrent ?? 0);
    if (sortField === 'devicesToday')
        return Number(row.devicesCurrent ?? 0);
    if (sortField === 'visitsTotal' || sortField === 'visitsCurrent' || sortField === 'visitsPrevious' || sortField === 'devicesTotal' || sortField === 'devicesCurrent' || sortField === 'devicesPrevious') {
        return Number(row[sortField] ?? 0);
    }
    if (sortField.startsWith('collect.')) {
        const key = sortField.slice('collect.'.length);
        return readPathValue(row.collectAmount, [key, 'total']);
    }
    const segments = sortField.split('.');
    if (segments[0] === 'dataCounts') {
        return readPathValue(row.dataCounts, segments.slice(1));
    }
    if (segments[0] === 'collectAmount') {
        return readPathValue(row.collectAmount, segments.slice(1));
    }
    return 0;
}
export function sortRows(rows, sortField, sortOrder) {
    const direction = sortOrder === 'asc' ? 1 : -1;
    return [...rows].sort((a, b) => {
        const diff = readSortValue(a, sortField) - readSortValue(b, sortField);
        if (diff !== 0)
            return diff * direction;
        return a.channelName.localeCompare(b.channelName, 'zh-CN');
    });
}
export function paginateRows(rows, page, pageSize) {
    const start = (page - 1) * pageSize;
    return rows.slice(start, start + pageSize);
}
//# sourceMappingURL=sort.js.map