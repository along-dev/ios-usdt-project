import { formatShanghaiDate, getShanghaiDayRange } from '../core/channel-stats/date.js';
import { IpSyncLog, StatsCheckpoint } from '../core/db/models/index.js';
import { logger } from '../core/logger/index.js';
const RETAIN_DAYS = 5;
const TIMEZONE = 'Asia/Shanghai';
const CHECKPOINT_TYPE = 'channel_stats';
const DAY_MS = 24 * 60 * 60 * 1000;
const DELETE_BATCH_SIZE = 5000;
const DELETE_BATCH_DELAY_MS = 100;
function getCutoff() {
    const dateKey = formatShanghaiDate(new Date(Date.now() - RETAIN_DAYS * DAY_MS));
    return { dateKey, start: getShanghaiDayRange(dateKey).start };
}
function sleep(ms) {
    if (ms <= 0)
        return Promise.resolve();
    return new Promise((resolve) => setTimeout(resolve, ms));
}
export const ipSyncCleanup = {
    name: 'ip-sync-cleanup',
    type: 'cron',
    cronExpression: '0 2 * * *',
    timezone: TIMEZONE,
    instanceOnly: 0,
    preventOverrun: true,
    handler: async () => {
        const startedAt = Date.now();
        const { dateKey: cutoffDateKey, start: cutoffStart } = getCutoff();
        const dateBuckets = await IpSyncLog.aggregate([
            { $match: { createdAt: { $lt: cutoffStart } } },
            {
                $group: {
                    _id: {
                        $dateToString: {
                            format: '%Y-%m-%d',
                            date: '$createdAt',
                            timezone: TIMEZONE,
                        },
                    },
                },
            },
            { $sort: { _id: 1 } },
        ]);
        const candidateDates = dateBuckets.map((bucket) => bucket._id).filter((date) => Boolean(date));
        if (candidateDates.length === 0) {
            logger.info({ retainDays: RETAIN_DAYS, cutoffDateKey }, 'ip-sync-cleanup completed');
            return;
        }
        const protectedDates = new Set(await StatsCheckpoint.distinct('date', {
            type: CHECKPOINT_TYPE,
            status: 'completed',
            date: { $in: candidateDates },
        }));
        let deletedDocs = 0;
        const deletedDates = [];
        const skippedDates = [];
        for (const date of candidateDates) {
            if (!protectedDates.has(date)) {
                skippedDates.push(date);
                continue;
            }
            const { start, end } = getShanghaiDayRange(date);
            let dateDeletedDocs = 0;
            let batch = 0;
            const dateStartedAt = Date.now();
            while (true) {
                const docs = await IpSyncLog.find({ createdAt: { $gte: start, $lt: end } }, { _id: 1 })
                    .sort({ _id: 1 })
                    .limit(DELETE_BATCH_SIZE)
                    .lean();
                if (docs.length === 0)
                    break;
                batch += 1;
                const ids = docs.map((doc) => doc._id).filter(Boolean);
                if (ids.length === 0)
                    break;
                const result = await IpSyncLog.deleteMany({ _id: { $in: ids } });
                const deletedInBatch = result.deletedCount ?? 0;
                dateDeletedDocs += deletedInBatch;
                deletedDocs += deletedInBatch;
                logger.info({
                    date,
                    batch,
                    batchSize: DELETE_BATCH_SIZE,
                    selectedDocs: ids.length,
                    deletedInBatch,
                    deletedSoFar: dateDeletedDocs,
                    durationMs: Date.now() - dateStartedAt,
                }, 'ip-sync-cleanup batch completed');
                if (docs.length < DELETE_BATCH_SIZE)
                    break;
                await sleep(DELETE_BATCH_DELAY_MS);
            }
            deletedDates.push(date);
            logger.info({
                date,
                batches: batch,
                deletedDocs: dateDeletedDocs,
                durationMs: Date.now() - dateStartedAt,
            }, 'ip-sync-cleanup date completed');
        }
        logger.info({
            retainDays: RETAIN_DAYS,
            deleteBatchSize: DELETE_BATCH_SIZE,
            deleteBatchDelayMs: DELETE_BATCH_DELAY_MS,
            cutoffDateKey,
            candidateDates: candidateDates.length,
            deletedDates,
            skippedDates,
            deletedDocs,
            durationMs: Date.now() - startedAt,
        }, 'ip-sync-cleanup completed');
    },
};
//# sourceMappingURL=ip-sync-cleanup.js.map