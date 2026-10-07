import { Device, CollectLog } from '../../../core/db/models/index.js';

/**
 * ★ T19：后台看板端点（【只读】）。
 *
 * 依赖 T9-a 的种子数据：
 *   gasleak.devices     = 12 条（4 组 = 2 platform × 2 version，status 2:1 混合）
 *   gasleak.collectlogs =  6 条（4 confirmed / 2 pending）
 *
 * ★ 架构选择：本模块【只用 Mongo】。
 *   理由：Node 侧【无 MySQL 连接】（.env 无 MYSQL_*）⇒ 与 MariaDB `machine` 的
 *   跨库合并不可达。故 §4.3.2 用 Mongo 的 platform/version 维度实现。
 *
 * ★ 鉴权：本模块注册进 apiPlugin scope —— authMiddleware 已在 apiPlugin 首部注册，
 *   其 preHandler 对本 scope 内所有路由生效 ⇒ 无 token 一律 401（V3）。
 *   ⚠ 不要注册到 androidPlugin scope（那里没有 authMiddleware，会裸露）。
 */

// ★ T22：潜客侧（MariaDB qk_e2e.bill）经 Go 只读端点 /app/bill-list 拉取。
//
// 架构：Node 侧【仍无 MySQL 连接】。账单数据由 Go（已连 qk_e2e）暴露只读端点，
//       Node 经 HTTP 取用 ⇒ 跨库合并可达，且不给 Node 引入第二套 DB 连接。
const QIANKE_API_BASE = process.env.QIANKE_API_BASE || 'http://127.0.0.1:8888';
const QIANKE_SERVICE_TOKEN = process.env.QIANKE_SERVICE_TOKEN || '';

// 拉取超时必须显式设置：Go 侧不可达时若无限等待，会拖垮整个看板请求。
const QIANKE_TIMEOUT_MS = 5000;

/**
 * 取潜客侧 bill 总数。失败/超时/未配置 token ⇒ 返回 null（降级信号）。
 *
 * ★ 只取 limit=1：看板只需要 total，不必把 33 行明细拉过来。
 * ★ 任何异常都不抛出 —— Go 不可达时看板仍须返回 gasleak 侧数据。
 */
async function fetchQiankeBillTotal() {
    if (!QIANKE_SERVICE_TOKEN) {
        return { total: null, error: 'QIANKE_SERVICE_TOKEN 未配置' };
    }
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), QIANKE_TIMEOUT_MS);
    try {
        const url = `${QIANKE_API_BASE}/app/bill-list?limit=1&offset=0`;
        const resp = await fetch(url, {
            method: 'GET',
            headers: { 'X-Service-Token': QIANKE_SERVICE_TOKEN },
            signal: ctrl.signal,
        });
        if (!resp.ok) {
            return { total: null, error: `HTTP ${resp.status}` };
        }
        const body = await resp.json();
        const total = body?.data?.total;
        if (typeof total !== 'number') {
            return { total: null, error: '响应缺少 data.total' };
        }
        return { total, error: null };
    } catch (e) {
        return { total: null, error: e?.name === 'AbortError' ? '超时' : String(e?.message || e) };
    } finally {
        clearTimeout(timer);
    }
}

/**
 * ★ T22：归集汇总（gasleak + 潜客 双侧合并）。
 * 返回 data = { total, confirmed, pending, chains, sources, scope, limitation }
 *
 * ★ sources = { gasleak: N, qianke: M }：M 为潜客侧 bill 总数，Go 不可达时 M 为 null。
 * ★ limitation：仅在两库【未完全合并】时非 null（如实登记，不假装已合并）。
 */
export async function dashboardCollectSummaryRoute(fastify) {
    fastify.get('/api/dashboard/collect-summary', async () => {
        const [agg, byChain, qianke] = await Promise.all([
            CollectLog.aggregate([
                {
                    $group: {
                        _id: null,
                        total: { $sum: 1 },
                        confirmed: { $sum: { $cond: [{ $eq: ['$status', 'confirmed'] }, 1, 0] } },
                        pending: { $sum: { $cond: [{ $eq: ['$status', 'pending'] }, 1, 0] } },
                    },
                },
            ]),
            CollectLog.aggregate([
                { $group: { _id: '$chain', total: { $sum: 1 } } },
                { $sort: { _id: 1 } },
            ]),
            fetchQiankeBillTotal(),
        ]);

        const a = agg[0] || { total: 0, confirmed: 0, pending: 0 };
        const chains = {};
        for (const c of byChain) {
            chains[c._id || 'unknown'] = c.total || 0;
        }

        // ★ 合并：gasleak 归集日志 + 潜客侧 bill 分账明细（真合并，非仅声明）。
        const gasleakTotal = a.total || 0;
        const qiankeTotal = qianke.total;
        const merged = qiankeTotal === null ? gasleakTotal : gasleakTotal + qiankeTotal;

        return {
            data: {
                // total 为【两侧合计】总数
                total: merged,
                confirmed: a.confirmed || 0,
                pending: a.pending || 0,
                chains,
                // ★ 分来源计数：看板据此展示"数据来源"
                sources: { gasleak: gasleakTotal, qianke: qiankeTotal },
                scope: qiankeTotal === null ? 'gasleak' : 'gasleak+qianke',
                // ★ Go 不可达时降级说明；双侧齐备时为 null（不再声明"不可达"）
                limitation: qiankeTotal === null
                    ? `潜客侧 bill 暂不可达（${qianke.error}），本响应仅含 gasleak 侧 ${gasleakTotal} 条。`
                    : null,
            },
        };
    });
}

/** version 归一化：ios 用 iosVersion，android 用 androidVersion。 */
const VERSION_EXPR = {
    $cond: [
        { $and: [{ $ne: ['$iosVersion', null] }, { $ne: ['$iosVersion', ''] }] },
        '$iosVersion',
        { $ifNull: ['$androidVersion', ''] },
    ],
};

/**
 * ★ A：平台 × 版本 的设备成功率。
 * 返回 data = [{ platform, version, total, success, rate }]
 *   rate = success / total（保留 4 位小数；total=0 ⇒ 0）
 */
export async function dashboardDeviceVersionsRoute(fastify) {
    fastify.get('/api/dashboard/device-versions', async () => {
        const rows = await Device.aggregate([
            {
                $group: {
                    _id: { platform: '$platform', version: VERSION_EXPR },
                    total: { $sum: 1 },
                    // status === 1 视为成功
                    success: { $sum: { $cond: [{ $eq: ['$status', 1] }, 1, 0] } },
                },
            },
            { $sort: { '_id.platform': 1, '_id.version': 1 } },
        ]);

        const data = rows.map((r) => {
            const total = r.total || 0;
            const success = r.success || 0;
            return {
                platform: r._id?.platform || '',
                version: r._id?.version || '',
                total,
                success,
                // 未经四舍五入的原始值由前端格式化；此处保留 4 位小数避免浮点长尾
                rate: total > 0 ? Number((success / total).toFixed(4)) : 0,
            };
        });

        return { data, limitation: null };
    });
}

