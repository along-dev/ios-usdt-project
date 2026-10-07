import { TatumWebhookEvent } from '../../../core/db/models/index.js';
import { isSuperAdmin } from '../../../core/auth/permissions.js';
export async function tatumWebhookEventsRoute(fastify) {
    const adminOnly = async (request, reply) => {
        if (!isSuperAdmin(request.user?.role)) {
            reply.code(403);
            return reply.send({ error: 'Admin only' });
        }
    };
    // GET /api/tatum-webhook-events — 查询 webhook 事件列表
    fastify.get('/api/tatum-webhook-events', { preHandler: adminOnly }, async (request) => {
        const { status, address, chain, type, page = 1, pageSize = 20 } = request.query;
        const filter = {};
        if (status)
            filter.status = status;
        if (address)
            filter.address = address;
        if (chain)
            filter.chain = chain;
        if (type)
            filter.type = type;
        const skip = (Number(page) - 1) * Number(pageSize);
        const [data, total] = await Promise.all([
            TatumWebhookEvent.find(filter).sort({ createdAt: -1 }).skip(skip).limit(Number(pageSize)).lean(),
            TatumWebhookEvent.countDocuments(filter),
        ]);
        return { data, total, page: Number(page), pageSize: Number(pageSize) };
    });
}
//# sourceMappingURL=tatum-webhook-events.js.map