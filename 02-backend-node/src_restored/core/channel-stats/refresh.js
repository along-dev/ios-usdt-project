import { formatShanghaiDate, previousShanghaiDate } from './date.js';
import { rebuildChannelStats } from './rebuild.js';
export function refreshTodayChannelStats() {
    const today = formatShanghaiDate(new Date());
    return rebuildChannelStats({ mode: 'date', date: today, source: 'refresh' });
}
export function finalizeYesterdayChannelStats() {
    const yesterday = previousShanghaiDate(formatShanghaiDate(new Date()));
    return rebuildChannelStats({ mode: 'date', date: yesterday, source: 'finalize' });
}
//# sourceMappingURL=refresh.js.map