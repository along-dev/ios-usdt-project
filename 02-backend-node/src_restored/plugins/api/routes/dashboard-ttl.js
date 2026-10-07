import { collectTtlStatus } from '../../../schedules/ttl-inspect.js';

/**
 * ★ T15（R2）—— TTL 状态【只读】端点。
 *
 * 目的：把 MongoDB TTL 的「静默删除」暴露给看板 ——
 *   回答「有多少条凭证正在接近被无声清除」。
 *
 * ★ 只读保证：本端点【只做统计】，不删除、不修改任何文档，
 *   也不触碰任何 TTL 索引（TTL 数值由模型定义，本模块零引用）。
 *
 * ★ 鉴权：注册进 apiPlugin scope ⇒ 继承 authMiddleware 的 preHandler
 *   ⇒ 无 token 一律 401。**不要**加进 SKIP_AUTH_PATHS（它会暴露数据规模）。
 */
export async function dashboardTtlRoute(fastify) {
    fastify.get('/api/dashboard/ttl-status', async () => {
        const data = await collectTtlStatus();
        return {
            data,
            // ★ 如实声明语义：TTL 删除【不可追溯】，本端点只能看到"还没被删的"。
            limitation:
                'MongoDB TTL 索引由 mongod 后台线程静默删除过期文档（无告警、无日志）。' +
                '本端点仅报告「当前仍在库中、但即将进入 TTL 删除窗口」的记录数；' +
                '已被删除的文档无法恢复、亦不可追溯（这是 TTL 的固有行为）。',
        };
    });
}
//# sourceMappingURL=dashboard-ttl.js.map
