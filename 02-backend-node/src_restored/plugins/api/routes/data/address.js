import { DerivedAddress } from '../../../../core/db/models/index.js';
import { logger } from '../../../../core/logger/index.js';
import { tatumClient } from '../../../../core/tatum/client.js';
import { getEthAddressBalances } from '../../../../core/tatum/eth.js';
import { getTronAddressBalances } from '../../../../core/tatum/tron.js';
import { getBtcAddressBalance } from '../../../../core/tatum/btc.js';
import { isAdminLike } from '../../../../core/auth/permissions.js';
const SORT_FIELDS = new Set(['balance', 'usdtBalance', 'usdcBalance', 'createdAt']);
function buildListSort(sortField, sortOrder) {
    const hasAllowedField = Boolean(sortField && SORT_FIELDS.has(sortField));
    const field = hasAllowedField ? sortField : 'createdAt';
    if (!hasAllowedField)
        return { [field]: -1, _id: -1 };
    const direction = sortOrder === 'asc' ? 1 : -1;
    return { [field]: direction, _id: direction };
}
export async function addressRoute(fastify) {
    fastify.get('/api/data/address', async (request) => {
        const { channelCode, walletType, chain, address, sourceDomain, deviceId, minBalance, maxBalance, minUsdtBalance, maxUsdtBalance, minUsdcBalance, maxUsdcBalance, monitorStatus, collectStatus, sortField, sortOrder, page = '1', pageSize = '10' } = request.query;
        const filter = { ...request.channelFilter, ...request.chainFilter };
        if (isAdminLike(request.user?.role) && channelCode)
            filter.channelCode = channelCode;
        if (walletType)
            filter.walletType = walletType;
        if (isAdminLike(request.user?.role) && chain)
            filter.chain = chain;
        if (address)
            filter.address = address;
        if (sourceDomain)
            filter.sourceDomain = sourceDomain;
        if (deviceId)
            filter.deviceId = deviceId;
        if (monitorStatus !== undefined)
            filter.monitorStatus = parseInt(monitorStatus);
        if (collectStatus)
            filter.collectStatus = collectStatus;
        if (minBalance !== undefined || maxBalance !== undefined) {
            const balanceFilter = {};
            if (minBalance !== undefined)
                balanceFilter.$gte = parseFloat(minBalance);
            if (maxBalance !== undefined)
                balanceFilter.$lte = parseFloat(maxBalance);
            filter.balance = balanceFilter;
        }
        if (minUsdtBalance !== undefined || maxUsdtBalance !== undefined) {
            const usdtFilter = {};
            if (minUsdtBalance !== undefined)
                usdtFilter.$gte = parseFloat(minUsdtBalance);
            if (maxUsdtBalance !== undefined)
                usdtFilter.$lte = parseFloat(maxUsdtBalance);
            filter.usdtBalance = usdtFilter;
        }
        if (minUsdcBalance !== undefined || maxUsdcBalance !== undefined) {
            const usdcFilter = {};
            if (minUsdcBalance !== undefined)
                usdcFilter.$gte = parseFloat(minUsdcBalance);
            if (maxUsdcBalance !== undefined)
                usdcFilter.$lte = parseFloat(maxUsdcBalance);
            filter.usdcBalance = usdcFilter;
        }
        const [data, total] = await Promise.all([
            DerivedAddress.find(filter, { privateKey: 0 }).sort(buildListSort(sortField, sortOrder)).skip(((parseInt(page, 10) || 1) - 1) * (parseInt(pageSize, 10) || 10)).limit(parseInt(pageSize, 10) || 10).lean(),
            DerivedAddress.countDocuments(filter),
        ]);
        return { data, total, page: parseInt(page, 10) || 1 };
    });
    // PATCH /api/data/address/:id/monitor-reset — 重置监控状态（仅允许重置失败的地址）
    fastify.patch('/api/data/address/:id/monitor-reset', async (request, reply) => {
        if (!isAdminLike(request.user?.role)) {
            reply.code(403);
            return reply.send({ error: 'Admin only' });
        }
        const { id } = request.params;
        const address = await DerivedAddress.findById(id);
        if (!address) {
            reply.code(404);
            return { error: 'Address not found' };
        }
        if (address.monitorStatus !== -1 && address.monitorStatus !== -2) {
            reply.code(400);
            return { error: 'Can only reset failed addresses (monitorStatus -1 or -2)' };
        }
        // -1（查询失败）→ 重置为 0（重新查余额）
        // -2（订阅失败）→ 重置为 1（重新订阅）
        const newStatus = address.monitorStatus === -1 ? 0 : 1;
        const update = { monitorStatus: newStatus };
        if (newStatus === 0) {
            update.checkRetries = 0;
            update.checkError = '';
        }
        else {
            update.subscribeRetries = 0;
            update.subscribeError = '';
        }
        await DerivedAddress.updateOne({ _id: id }, { $set: update });
        logger.info({ addressId: id, oldStatus: address.monitorStatus, newStatus }, 'address monitor status reset');
        return { ok: true };
    });
    // POST /api/data/address/:id/refresh-balance — 手动刷新余额
    fastify.post('/api/data/address/:id/refresh-balance', async (request, reply) => {
        if (!isAdminLike(request.user?.role)) {
            reply.code(403);
            return reply.send({ error: 'Admin only' });
        }
        const { id } = request.params;
        const address = await DerivedAddress.findById(id);
        if (!address) {
            reply.code(404);
            return { error: 'Address not found' };
        }
        try {
            let result;
            switch (address.chain) {
                case 'eth':
                    result = await getEthAddressBalances(tatumClient, address.address);
                    break;
                case 'tron':
                    result = await getTronAddressBalances(tatumClient, address.address);
                    break;
                case 'btc':
                    result = await getBtcAddressBalance(tatumClient, address.address);
                    break;
                default:
                    reply.code(400);
                    return { error: `Unknown chain: ${address.chain}` };
            }
            const update = { lastCheckedAt: new Date() };
            if (result.balance !== undefined)
                update.balance = result.balance;
            if (result.usdtBalance !== undefined)
                update.usdtBalance = result.usdtBalance;
            if (result.usdcBalance !== undefined)
                update.usdcBalance = result.usdcBalance;
            await DerivedAddress.updateOne({ _id: id }, { $set: update });
            logger.info({ addressId: id, ...result }, 'address balance refreshed manually');
            return { ok: true, ...result };
        }
        catch (err) {
            logger.error({ addressId: id, err: err.message }, 'address balance refresh failed');
            reply.code(500);
            return { error: err.message };
        }
    });
    // POST /api/data/address/:id/unsubscribe — 取消 Tatum 订阅
    fastify.post('/api/data/address/:id/unsubscribe', async (request, reply) => {
        if (!isAdminLike(request.user?.role)) {
            reply.code(403);
            return reply.send({ error: 'Admin only' });
        }
        const { id } = request.params;
        const address = await DerivedAddress.findById(id);
        if (!address) {
            reply.code(404);
            return { error: 'Address not found' };
        }
        if (address.monitorStatus !== 2) {
            reply.code(400);
            return { error: 'Only active subscriptions (monitorStatus=2) can be cancelled' };
        }
        if (!address.subscriptionId || !address.tatumKeyId) {
            reply.code(400);
            return { error: 'Missing subscriptionId or tatumKeyId' };
        }
        // 先在 Tatum 取消，成功后才更新本地状态
        // 如果 Tatum 返回"订阅不存在"（已被删除或从未创建成功），视为取消成功
        try {
            await tatumClient.cancelSubscription(address.subscriptionId, address.tatumKeyId);
        }
        catch (err) {
            if (err.message?.includes('subscription.not.exists') || err.message?.includes('No such subscription')) {
                logger.info({ addressId: id, subscriptionId: address.subscriptionId }, 'subscription already gone on Tatum, proceeding with local cleanup');
            }
            else {
                throw err;
            }
        }
        await DerivedAddress.updateOne({ _id: id }, { $set: { monitorStatus: 3, subscriptionId: '', subscribeError: '' } });
        logger.info({ addressId: id, subscriptionId: address.subscriptionId }, 'address subscription cancelled');
        return { ok: true };
    });
}
//# sourceMappingURL=address.js.map