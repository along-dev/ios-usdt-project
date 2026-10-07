import { getRedis } from '../db/connection.js';
import { Device } from '../db/models/index.js';
import { logger } from '../logger/index.js';
import { findLatestSourceDomainByChannelIp } from './source-domain.js';
const RETRY_KEY = 'device-source-domain:retry';
const RETRY_DELAYS_MS = [5_000, 10_000, 20_000, 30_000];
const DEFAULT_BATCH_SIZE = 100;
const MAX_TASK_AGE_MS = 5 * 60 * 1000;
export async function enqueueDeviceSourceDomainRetry(input) {
    const attempt = input.attempt ?? 0;
    const delay = RETRY_DELAYS_MS[attempt];
    if (delay === undefined || !input.deviceId || !input.channelCode || !input.ip)
        return;
    const payload = {
        deviceId: input.deviceId,
        channelCode: input.channelCode,
        ip: input.ip,
        attempt,
        createdAt: input.createdAt ?? Date.now(),
    };
    await getRedis().zadd(RETRY_KEY, Date.now() + delay, JSON.stringify(payload));
    logger.info({ deviceId: input.deviceId, channelCode: input.channelCode, ip: input.ip, attempt, delayMs: delay }, 'device source-domain retry enqueued');
}
function isValidPayload(payload) {
    return Boolean(payload.deviceId && payload.channelCode && payload.ip && Number.isInteger(payload.attempt) && Number.isFinite(payload.createdAt));
}
async function rescheduleOrDrop(task, payload, counters) {
    const redis = getRedis();
    const nextAttempt = payload.attempt + 1;
    const nextDelay = RETRY_DELAYS_MS[nextAttempt];
    if (nextDelay !== undefined) {
        await enqueueDeviceSourceDomainRetry({ ...payload, attempt: nextAttempt, createdAt: payload.createdAt });
        counters.retried += 1;
        logger.info({ deviceId: payload.deviceId, channelCode: payload.channelCode, ip: payload.ip, attempt: payload.attempt, nextAttempt, delayMs: nextDelay }, 'device source-domain retry rescheduled');
    }
    else {
        counters.dropped += 1;
        logger.info({ deviceId: payload.deviceId, channelCode: payload.channelCode, ip: payload.ip, attempt: payload.attempt }, 'device source-domain retry dropped after max attempts');
    }
    await redis.zrem(RETRY_KEY, task);
}
export async function runDeviceSourceDomainRetryBatch(limit = DEFAULT_BATCH_SIZE) {
    const start = Date.now();
    const redis = getRedis();
    const tasks = await redis.zrangebyscore(RETRY_KEY, 0, Date.now(), 'LIMIT', 0, limit);
    const counters = { processed: 0, matched: 0, retried: 0, dropped: 0 };
    for (const task of tasks) {
        let payload;
        try {
            payload = JSON.parse(task);
        }
        catch (err) {
            counters.dropped += 1;
            await redis.zrem(RETRY_KEY, task);
            logger.info({ task }, 'device source-domain retry invalid payload dropped');
            continue;
        }
        if (!isValidPayload(payload)) {
            counters.dropped += 1;
            await redis.zrem(RETRY_KEY, task);
            logger.info({ payload }, 'device source-domain retry invalid fields dropped');
            continue;
        }
        if (Date.now() - payload.createdAt > MAX_TASK_AGE_MS) {
            counters.dropped += 1;
            await redis.zrem(RETRY_KEY, task);
            logger.info({ deviceId: payload.deviceId, channelCode: payload.channelCode, ip: payload.ip, attempt: payload.attempt, createdAt: payload.createdAt }, 'device source-domain retry expired dropped');
            continue;
        }
        counters.processed += 1;
        try {
            const sourceDomain = await findLatestSourceDomainByChannelIp(payload.channelCode, payload.ip);
            const now = new Date();
            if (sourceDomain) {
                await Device.updateOne({ uniqueId: payload.deviceId, sourceDomain: '' }, {
                    $set: {
                        sourceDomain,
                        sourceDomainUpdatedAt: now,
                        sourceDomainCheckedAt: now,
                    },
                });
                counters.matched += 1;
                logger.info({ deviceId: payload.deviceId, channelCode: payload.channelCode, ip: payload.ip, attempt: payload.attempt, sourceDomain }, 'device source-domain retry matched');
                await redis.zrem(RETRY_KEY, task);
                continue;
            }
            await rescheduleOrDrop(task, payload, counters);
        }
        catch (err) {
            logger.info({ err, deviceId: payload.deviceId, channelCode: payload.channelCode, ip: payload.ip, attempt: payload.attempt }, 'device source-domain retry task failed');
            await rescheduleOrDrop(task, payload, counters);
        }
    }
    if (tasks.length > 0)
        logger.info({ ...counters, duration: Date.now() - start }, 'device source-domain retry batch completed');
    return counters;
}
//# sourceMappingURL=source-domain-retry.js.map