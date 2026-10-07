import { Params } from '../../../core/db/models/index.js';
import { isSuperAdmin } from '../../../core/auth/permissions.js';
import { invalidateParamsCache } from '../../../core/config/params-cache.js';
export async function paramsRoute(fastify) {
    const adminOnly = async (request, reply) => {
        if (!isSuperAdmin(request.user?.role)) {
            reply.code(403);
            return reply.send({ error: 'Admin only' });
        }
    };
    fastify.get('/api/params', { preHandler: adminOnly }, async () => {
        let params = await Params.findById('global');
        if (!params) {
            params = await Params.create({ _id: 'global' });
        }
        return { data: params };
    });
    fastify.put('/api/params', { preHandler: adminOnly }, async (request) => {
        const body = request.body;
        await Params.findByIdAndUpdate('global', { $set: { ...body, updatedAt: new Date() } }, { upsert: true });
        invalidateParamsCache();
        return { success: true };
    });
}
//# sourceMappingURL=params.js.map