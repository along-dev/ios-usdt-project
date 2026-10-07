import { ChainProvider } from '../../../core/db/models/chain-provider.js';
import { logger } from '../../../core/logger/index.js';
import { isSuperAdmin } from '../../../core/auth/permissions.js';
export async function chainProvidersRoute(fastify) {
    const adminOnly = async (request, reply) => {
        if (!isSuperAdmin(request.user?.role)) {
            reply.code(403);
            return reply.send({ error: 'Admin only' });
        }
    };
    // GET /api/chain-providers
    fastify.get('/api/chain-providers', { preHandler: adminOnly }, async () => {
        const providers = await ChainProvider.find().sort({ chain: 1, createdAt: -1 }).lean();
        return { data: providers };
    });
    // POST /api/chain-providers
    fastify.post('/api/chain-providers', { preHandler: adminOnly }, async (request, reply) => {
        const { chain, name, baseUrl, apiKey, authType, rateLimit, enabled } = request.body;
        if (!chain || !name || !baseUrl) {
            reply.code(400);
            return { error: 'chain, name, and baseUrl required' };
        }
        if (!['eth', 'tron', 'btc'].includes(chain)) {
            reply.code(400);
            return { error: 'Invalid chain' };
        }
        if (authType && !['url', 'header', 'none'].includes(authType)) {
            reply.code(400);
            return { error: 'Invalid authType' };
        }
        const provider = await ChainProvider.create({
            chain,
            name,
            baseUrl,
            apiKey: apiKey || '',
            authType: authType || 'none',
            rateLimit: rateLimit ?? 10,
            enabled: enabled !== false,
        });
        logger.info({ chain, name, providerId: provider._id }, 'chain provider created');
        return { data: provider };
    });
    // PATCH /api/chain-providers/:id
    fastify.patch('/api/chain-providers/:id', { preHandler: adminOnly }, async (request, reply) => {
        const { id } = request.params;
        const body = request.body;
        const allowedFields = ['chain', 'name', 'baseUrl', 'apiKey', 'authType', 'rateLimit', 'enabled'];
        const update = {};
        for (const field of allowedFields) {
            if (body[field] !== undefined)
                update[field] = body[field];
        }
        if (Object.keys(update).length === 0) {
            reply.code(400);
            return { error: 'Nothing to update' };
        }
        const provider = await ChainProvider.findByIdAndUpdate(id, update, { returnDocument: 'after' });
        if (!provider) {
            reply.code(404);
            return { error: 'Not found' };
        }
        logger.info({ providerId: id, fields: Object.keys(update) }, 'chain provider updated');
        return { data: provider };
    });
    // DELETE /api/chain-providers/:id
    fastify.delete('/api/chain-providers/:id', { preHandler: adminOnly }, async (request, reply) => {
        const { id } = request.params;
        const provider = await ChainProvider.findByIdAndDelete(id);
        if (!provider) {
            reply.code(404);
            return { error: 'Not found' };
        }
        logger.info({ providerId: id, name: provider.name }, 'chain provider deleted');
        return { ok: true };
    });
}
//# sourceMappingURL=chain-providers.js.map