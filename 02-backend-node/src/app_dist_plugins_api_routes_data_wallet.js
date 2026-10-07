import { WalletData } from '../../../../core/db/models/index.js';
import { isAdminLike } from '../../../../core/auth/permissions.js';
function isAdmin(request) {
    return isAdminLike(request.user?.role);
}
function maskWalletDataValue(value) {
    if (value === null || value === undefined)
        return value;
    if (Array.isArray(value))
        return value.map(maskWalletDataValue);
    if (typeof value === 'object') {
        return Object.fromEntries(Object.entries(value).map(([key, child]) => [key, maskWalletDataValue(child)]));
    }
    return '***';
}
function maskWalletRow(row) {
    if (!row)
        return row;
    return { ...row, data: maskWalletDataValue(row.data) };
}
export async function walletRoute(fastify) {
    fastify.get('/api/data/wallet', async (request) => {
        const { channelCode, walletType, deviceId, sourceDomain, page = '1', pageSize = '10' } = request.query;
        const filter = { ...request.channelFilter };
        if (isAdmin(request) && channelCode)
            filter.channelCode = channelCode;
        if (walletType)
            filter.walletType = walletType;
        if (deviceId)
            filter.deviceId = deviceId;
        if (sourceDomain)
            filter.sourceDomain = sourceDomain;
        const skip = ((parseInt(page, 10) || 1) - 1) * (parseInt(pageSize, 10) || 10);
        const [data, total] = await Promise.all([
            WalletData.find(filter).sort({ receivedAt: -1 }).skip(skip).limit(parseInt(pageSize, 10) || 10).lean(),
            WalletData.countDocuments(filter),
        ]);
        return { data: isAdmin(request) ? data : data.map(maskWalletRow), total, page: parseInt(page, 10) || 1 };
    });
    fastify.get('/api/data/wallet/:id', async (request, reply) => {
        const { id } = request.params;
        const r = await WalletData.findById(id).lean();
        if (!r) {
            reply.code(404);
            return { error: 'Not found' };
        }
        return { data: isAdmin(request) ? r : maskWalletRow(r) };
    });
    fastify.delete('/api/data/wallet/:id', async (request, reply) => {
        if (!isAdmin(request)) {
            reply.code(403);
            return { error: 'Admin only' };
        }
        const { id } = request.params;
        await WalletData.deleteOne({ _id: id });
        return { success: true };
    });
}
//# sourceMappingURL=wallet.js.map