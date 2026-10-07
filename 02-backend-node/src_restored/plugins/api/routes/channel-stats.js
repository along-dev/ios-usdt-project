import { rebuildChannelStats } from '../../../core/channel-stats/rebuild.js';
import { recalcChannelStats } from '../../../core/channel-stats/recalc.js';
import { StatsCheckpoint } from '../../../core/db/models/index.js';
import { ChannelStatsAccessError, getChannelStatsPage } from '../../../core/channel-stats/query.js';
import { normalizeChannelStatsQuery } from '../../../core/channel-stats/sort.js';
import { isAdminLike } from '../../../core/auth/permissions.js';
async function adminOnly(request, reply) {
    if (!isAdminLike(request.user?.role)) {
        reply.code(403);
        await reply.send({ error: 'Admin only' });
    }
}
function isInvalidDateError(error) {
    return error instanceof Error && error.message.startsWith('Invalid date:');
}
export async function channelStatsRoute(fastify) {
    fastify.get('/api/channel-stats', async (request, reply) => {
        try {
            const query = normalizeChannelStatsQuery(request.query);
            const data = await getChannelStatsPage(request, query);
            return { data };
        }
        catch (error) {
            if (error instanceof ChannelStatsAccessError) {
                reply.code(403);
                return { error: error.message };
            }
            if (isInvalidDateError(error)) {
                reply.code(400);
                return { error: error.message };
            }
            throw error;
        }
    });
    fastify.get('/api/channel-stats/:channelCode/domains', async (request, reply) => {
        try {
            const query = normalizeChannelStatsQuery(request.query);
            const data = await getChannelStatsPage(request, { ...query, channelCode: request.params.channelCode });
            return { data };
        }
        catch (error) {
            if (error instanceof ChannelStatsAccessError) {
                reply.code(403);
                return { error: error.message };
            }
            if (isInvalidDateError(error)) {
                reply.code(400);
                return { error: error.message };
            }
            throw error;
        }
    });
    fastify.get('/api/channel-stats/checkpoints', { preHandler: adminOnly }, async (request) => {
        const query = request.query;
        const pageRaw = Number(query.page || 1);
        const pageSizeRaw = Number(query.pageSize || 10);
        const page = Number.isFinite(pageRaw) ? Math.max(Math.floor(pageRaw), 1) : 1;
        const pageSize = Number.isFinite(pageSizeRaw) ? Math.min(Math.max(Math.floor(pageSizeRaw), 1), 100) : 10;
        const filter = { type: 'channel_stats' };
        const [items, total] = await Promise.all([
            StatsCheckpoint.find(filter)
                .sort({ updatedAt: -1 })
                .skip((page - 1) * pageSize)
                .limit(pageSize)
                .lean(),
            StatsCheckpoint.countDocuments(filter),
        ]);
        return { data: { items, total } };
    });
    fastify.post('/api/channel-stats/rebuild', { preHandler: adminOnly }, async (request) => {
        const data = await rebuildChannelStats(request.body);
        return { data };
    });
    fastify.post('/api/channel-stats/recalc', { preHandler: adminOnly }, async (request) => {
        const { days } = (request.body || {});
        const data = await recalcChannelStats(days ? { days: Number(days) } : undefined);
        return { data };
    });
}
//# sourceMappingURL=channel-stats.js.map