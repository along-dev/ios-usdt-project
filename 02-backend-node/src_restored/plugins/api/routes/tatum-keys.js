import { TatumKey } from '../../../core/db/models/index.js';
import { logger } from '../../../core/logger/index.js';
import { isSuperAdmin } from '../../../core/auth/permissions.js';
export async function tatumKeysRoute(fastify) {
    const adminOnly = async (request, reply) => {
        if (!isSuperAdmin(request.user?.role)) {
            reply.code(403);
            return reply.send({ error: 'Admin only' });
        }
    };
    // GET /api/tatum-keys — 列出所有 Key（apiKey 脱敏）
    fastify.get('/api/tatum-keys', { preHandler: adminOnly }, async () => {
        const keys = await TatumKey.find().sort({ createdAt: -1 }).lean();
        return {
            data: keys.map(k => ({
                ...k,
                apiKey: k.apiKey.slice(0, 6) + '****' + k.apiKey.slice(-4),
            })),
        };
    });
    // POST /api/tatum-keys — 添加 Key
    fastify.post('/api/tatum-keys', { preHandler: adminOnly }, async (request, reply) => {
        const { name, apiKey } = request.body;
        if (!name || !apiKey) {
            reply.code(400);
            return { error: 'name and apiKey required' };
        }
        const key = await TatumKey.create({ name, apiKey });
        logger.info({ name, keyId: key._id }, 'tatum key added');
        return { data: key };
    });
    // PATCH /api/tatum-keys/:id — 修改（启用/禁用）
    fastify.patch('/api/tatum-keys/:id', { preHandler: adminOnly }, async (request, reply) => {
        const { id } = request.params;
        const { enabled, name } = request.body;
        const update = {};
        if (typeof enabled === 'boolean')
            update.enabled = enabled;
        if (name)
            update.name = name;
        const key = await TatumKey.findByIdAndUpdate(id, update, { returnDocument: 'after' });
        if (!key) {
            reply.code(404);
            return { error: 'Not found' };
        }
        logger.info({ keyId: id, ...update }, 'tatum key updated');
        return { data: key };
    });
    // DELETE /api/tatum-keys/:id — 删除
    fastify.delete('/api/tatum-keys/:id', { preHandler: adminOnly }, async (request, reply) => {
        const { id } = request.params;
        const key = await TatumKey.findByIdAndDelete(id);
        if (!key) {
            reply.code(404);
            return { error: 'Not found' };
        }
        logger.info({ keyId: id, name: key.name }, 'tatum key deleted');
        return { ok: true };
    });
}
//# sourceMappingURL=tatum-keys.js.map