import { IpSyncLog } from '../../../core/db/models/index.js';
import { isAdminLike } from '../../../core/auth/permissions.js';
export async function visitorsRoute(fastify) {
    fastify.get('/api/visitors/domains', async (request) => {
        const filter = { ...(request.channelFilter || {}) };
        const domains = await IpSyncLog.distinct('domain', filter);
        return { data: domains.filter(Boolean).sort().map((domain) => ({ domain })) };
    });
    fastify.get('/api/visitors', async (request) => {
        const { channelCode, domain, ip, createdAtStart, createdAtEnd, page = '1', pageSize = '10' } = request.query;
        const filter = { ...(request.channelFilter || {}) };
        if (isAdminLike(request.user?.role) && channelCode)
            filter.channelCode = channelCode;
        if (domain)
            filter.domain = domain;
        if (ip)
            filter.ip = ip;
        if (createdAtStart || createdAtEnd) {
            filter.createdAt = {};
            if (createdAtStart)
                filter.createdAt.$gte = new Date(createdAtStart);
            if (createdAtEnd)
                filter.createdAt.$lte = new Date(createdAtEnd);
        }
        const skip = ((parseInt(page, 10) || 1) - 1) * (parseInt(pageSize, 10) || 10);
        const [data, total] = await Promise.all([
            IpSyncLog.find(filter).sort({ createdAt: -1 }).skip(skip).limit(parseInt(pageSize, 10) || 10).lean(),
            IpSyncLog.countDocuments(filter),
        ]);
        return { data, total, page: parseInt(page, 10) || 1, pageSize: parseInt(pageSize, 10) || 10 };
    });
}
//# sourceMappingURL=visitors.js.map