import { WalletData, DeviceEvent } from '../core/db/models/index.js';
import { Task } from '../core/db/models/task.js';
import { logger } from '../core/logger/index.js';

/**
 * ★ T15（R2）—— P2-4 的 TTL 【可观测性】。
 *
 * ★ 为什么需要本任务（重要）：
 *   MongoDB 的 TTL 索引（`expireAfterSeconds`）由 mongod 的后台线程
 *   （默认每 60s 一轮）**静默删除**过期文档 ——
 *   **没有告警、没有日志、没有通知**。
 *   ⇒ `WalletData` / `device-event` 超期后，凭证**会无声消失且不可追溯**。
 *   ⇒ 这是 TTL 的【固有行为】，不是缺陷；缺陷是【我们没有观测到它】。
 *
 * ★ 本任务【只做观测】，**绝不改 TTL 数值、绝不删除任何数据**：
 *   1. 统计各集合「即将过期」的条数（进入 TTL 窗口尾部）；
 *   2. 统计各集合「最老一条」的年龄；
 *   3. 用 `logger.warn` 把结果写进日志 ⇒ 让"静默消失"变【可见】。
 *
 * ★ 为什么用 warn 而非 info：
 *   本任务的输出是【容量/合规风险的早期预警】——「有 N 条凭证将在 X 天内
 *   被 Mongo 静默删除」。这正是 P2-4 要求"可见"的东西，级别为 warn。
 *
 * ★ 性能（停靠点 2 的答复）：
 *   全部为 `countDocuments` + `findOne.sort`，且【只跑索引前缀】
 *   （`receivedAt: 1` / `createdAt: 1` 上就建了 TTL 索引 ⇒ 计数走索引，
 *   非全表扫描）。间隔 6 小时、单实例执行（instanceOnly: 0），
 *   ⇒ 对线上无可测量影响。
 */

// ---------------------------------------------------------------------------
// 被观测的集合 —— ★ 数值为【只读镜像】，与模型定义同源，本文件不改它们。
// ---------------------------------------------------------------------------
const TTL_TARGETS = [
    {
        collection: 'WalletData',
        model: WalletData,
        field: 'receivedAt',
        ttlDays: 30,
        // 进入最后 5 天即视为「即将过期」
        warnWithinDays: 5,
    },
    {
        collection: 'DeviceEvent',
        model: DeviceEvent,
        field: 'createdAt',
        ttlDays: 30,
        warnWithinDays: 5,
    },
    {
        collection: 'Task',
        model: Task,
        field: 'createdAt',
        ttlDays: 90,
        warnWithinDays: 7,
    },
];

const DAY_MS = 24 * 3600 * 1000;

/**
 * 统计单个集合的 TTL 状况。
 * ★ 只读：仅 countDocuments / findOne，无 delete、无 update。
 */
async function inspectOne(target, nowMs) {
    const { collection, model, field, ttlDays, warnWithinDays } = target;
    const ttlMs = ttlDays * DAY_MS;

    // 「即将过期窗口」的下界：age >= ttlDays - warnWithinDays
    const windowStart = new Date(nowMs - (ttlDays - warnWithinDays) * DAY_MS);
    // TTL 本身的过期线（由 mongod 执行；此处仅用于报告"理论上应已被删"的量）
    const expireLine = new Date(nowMs - ttlMs);

    const [total, expiringSoon, overdue, oldest] = await Promise.all([
        model.countDocuments({}),
        model.countDocuments({ [field]: { $lt: windowStart } }),
        model.countDocuments({ [field]: { $lt: expireLine } }),
        model.findOne({}, { [field]: 1 }).sort({ [field]: 1 }).lean(),
    ]);

    const oldestAt = oldest ? oldest[field] : null;
    const oldestAgeDays = oldestAt
        ? Number(((nowMs - new Date(oldestAt).getTime()) / DAY_MS).toFixed(2))
        : 0;

    return {
        collection,
        field,
        ttlDays,
        total,
        expiringSoon,
        overdue,
        oldestAgeDays,
    };
}

export const ttlInspect = {
    name: 'ttl-inspect',
    // ★ 6 小时一轮：TTL 以「天」为量级，无需高频；且避免与其它任务争抢 IO。
    interval: { hours: 6 },
    runImmediately: true,
    instanceOnly: 0,
    handler: async () => {
        const start = Date.now();
        const nowMs = Date.now();
        const report = [];
        try {
            for (const target of TTL_TARGETS) {
                try {
                    const row = await inspectOne(target, nowMs);
                    report.push(row);
                    // ★★ V2 核心：可观测性落地点 —— 每条都记录，字段含
                    //    collection / expiringSoon / oldestAgeDays。
                    logger.warn(
                        {
                            collection: row.collection,
                            field: row.field,
                            ttlDays: row.ttlDays,
                            total: row.total,
                            expiringSoon: row.expiringSoon,
                            overdue: row.overdue,
                            oldestAgeDays: row.oldestAgeDays,
                        },
                        'ttl-inspect: records approaching silent TTL deletion',
                    );
                } catch (err) {
                    // 单集合失败不影响其余集合
                    logger.error({ err, collection: target.collection }, 'ttl-inspect: collection scan failed');
                }
            }

            const expiringTotal = report.reduce((s, r) => s + (r.expiringSoon || 0), 0);
            const summary = {
                collections: report,
                expiringSoonTotal: expiringTotal,
                duration: Date.now() - start,
            };
            logger.warn(summary, 'ttl-inspect completed');
            return summary;
        } catch (err) {
            logger.error({ err, duration: Date.now() - start }, 'ttl-inspect failed');
            return null;
        }
    },
};

/**
 * ★ 供只读端点复用的巡检函数（不写日志，直接返回结构化结果）。
 * 端点与定时任务共用同一份统计口径 ⇒ 看板与日志不会出现两套数字。
 */
export async function collectTtlStatus() {
    const nowMs = Date.now();
    const collections = [];
    for (const target of TTL_TARGETS) {
        try {
            collections.push(await inspectOne(target, nowMs));
        } catch (err) {
            collections.push({
                collection: target.collection,
                field: target.field,
                ttlDays: target.ttlDays,
                error: String(err && err.message ? err.message : err),
            });
        }
    }
    return {
        generatedAt: new Date(nowMs).toISOString(),
        collections,
        expiringSoonTotal: collections.reduce((s, r) => s + (r.expiringSoon || 0), 0),
    };
}

//# sourceMappingURL=ttl-inspect.js.map
