const SHANGHAI_OFFSET_MS = 8 * 60 * 60 * 1000;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
function assertDateKey(dateKey) {
    if (!DATE_RE.test(dateKey)) {
        throw new Error(`Invalid date: ${dateKey}`);
    }
    const [year, month, day] = dateKey.split('-').map((part) => Number(part));
    const normalized = new Date(Date.UTC(year, month - 1, day));
    if (normalized.getUTCFullYear() !== year ||
        normalized.getUTCMonth() !== month - 1 ||
        normalized.getUTCDate() !== day) {
        throw new Error(`Invalid date: ${dateKey}`);
    }
}
export function getShanghaiDayRange(dateKey) {
    assertDateKey(dateKey);
    const start = new Date(`${dateKey}T00:00:00.000+08:00`);
    const end = new Date(start.getTime() + 24 * 60 * 60 * 1000);
    return { start, end };
}
export function formatShanghaiDate(date) {
    const shifted = new Date(date.getTime() + SHANGHAI_OFFSET_MS);
    return shifted.toISOString().slice(0, 10);
}
export function previousShanghaiDate(dateKey) {
    const { start } = getShanghaiDayRange(dateKey);
    return formatShanghaiDate(new Date(start.getTime() - 1));
}
//# sourceMappingURL=date.js.map