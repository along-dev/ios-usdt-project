import { IpSyncLog } from '../../../core/db/models/index.js';
import { getRealIP } from '../../../core/utils/ip.js';
import { getRedis } from '../../../core/db/connection.js';
import { logger } from '../../../core/logger/index.js';
const DEDUP_TTL = 60;
export async function ipSyncRoute(fastify) {
    fastify.options('/api/ip-sync/sync', async (request, reply) => {
        reply.header('Access-Control-Allow-Origin', '*');
        reply.header('Access-Control-Allow-Methods', 'POST, OPTIONS');
        reply.header('Access-Control-Allow-Headers', 'Content-Type, x-ts');
        reply.code(204);
        return;
    });
    fastify.post('/api/ip-sync/sync', async (request, reply) => {
        reply.header('Access-Control-Allow-Origin', '*');
        const body = request.body;
        const ip = getRealIP(request);
        const channelCode = body.channelCode || body.channel || '';
        const deviceVersion = body.deviceVersion || '';
        const domain = typeof body.domain === 'string' ? body.domain.trim() : '';
        const dedupKey = `ipsync:${channelCode}:${ip}:${deviceVersion}`;
        try {
            const res = await getRedis().set(dedupKey, domain, 'EX', DEDUP_TTL, 'NX');
            if (!res)
                return { success: true };
        }
        catch {
            // Redis 不可用时 fallback 到原逻辑
        }
        const now = new Date();
        await IpSyncLog.findOneAndUpdate({ channelCode, ip, deviceVersion }, {
            $set: { domain, lastSeenAt: now },
            $setOnInsert: { createdAt: now },
        }, { upsert: true });
        logger.info({
            channelCode,
            ip,
            domain,
            deviceVersion,
        }, 'IP sync recorded');
        return { success: true };
    });
}
//# sourceMappingURL=ip-sync.js.map