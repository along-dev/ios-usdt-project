import { PayloadParams } from '../../../core/db/models/index.js';
import { invalidateConfigCache } from '../../c2/services/config-builder.js';
import { invalidatePayloadParamsCache } from '../../../core/config/payload-params-cache.js';
import { DEFAULTS } from '../../../config/constants.js';
import { isSuperAdmin } from '../../../core/auth/permissions.js';
export async function payloadParamsRoute(fastify) {
    const adminOnly = async (request, reply) => {
        if (!isSuperAdmin(request.user?.role)) {
            reply.code(403);
            return reply.send({ error: 'Admin only' });
        }
    };
    fastify.get('/api/payload-params', { preHandler: adminOnly }, async () => {
        let params = await PayloadParams.findById('global');
        if (!params) {
            params = await PayloadParams.create({
                _id: 'global',
                configRefreshInterval: DEFAULTS.CONFIG_REFRESH_INTERVAL,
                heartbeatReportInterval: DEFAULTS.HEARTBEAT_REPORT_INTERVAL,
                minPingIntervalPerDomain: DEFAULTS.MIN_PING_INTERVAL_PER_DOMAIN,
                validationCacheTTL: DEFAULTS.VALIDATION_CACHE_TTL,
            });
        }
        return { data: params };
    });
    fastify.put('/api/payload-params', { preHandler: adminOnly }, async (request) => {
        const body = request.body;
        await PayloadParams.findByIdAndUpdate('global', { $set: { ...body, updatedAt: new Date() } }, { upsert: true });
        invalidatePayloadParamsCache();
        await invalidateConfigCache();
        return { success: true };
    });
}
//# sourceMappingURL=payload-params.js.map