import crypto from 'node:crypto';
import { createReadStream } from 'node:fs';
import { stat, rm } from 'node:fs/promises';
import path from 'node:path';
import bcrypt from 'bcryptjs';
import { Channel, Device, Role, User } from '../../../core/db/models/index.js';
import { createChannel, regenerateChannelZip } from '../../channel/services/creator.js';
import { loadConfig } from '../../../config/index.js';
import { logger } from '../../../core/logger/index.js';
import { isAdminLike } from '../../../core/auth/permissions.js';
import { KNOWN_TEMPLATES } from '../../android/landing.js';

// ★ W-AD-01/06：数据范围收口。
//   注意【字段名错位】：本模型的字段是 `code`，而 `request.channelFilter` 的键是
//   `channelCode`（auth.js:91 是给统计类模型设的）⇒ 不能直接把 channelFilter 展开进本模型的查询。
//   非 adminLike 且 channelCodes 为空 ⇒ `{$in: []}` ⇒ 空集（**不是**全量），这是反向判据的支点。
function buildChannelScopeFilter(request) {
    if (isAdminLike(request.user?.role))
        return {};
    const raw = Array.isArray(request.user?.channelCodes) ? request.user.channelCodes : [];
    const codes = [...new Set(raw
            .filter((c) => typeof c === 'string' && c.trim())
            .map((c) => c.trim()))];
    return { code: { $in: codes } };
}

function scopedQuery(scope, base) {
    return Object.keys(scope).length > 0 ? { $and: [base, scope] } : base;
}

// 外键归一化：非负整数或 null 合法；其余返回 undefined 表示非法。
function normalizeForeignId(raw) {
    if (raw === null || raw === undefined || raw === '')
        return null;
    const n = Number(raw);
    return Number.isInteger(n) && n >= 0 ? n : undefined;
}

/** 校验并抽取 W-AD-01/05 的绑定字段；返回 { ok:true, value } 或 { ok:false, error } */
function normalizeBinding(body) {
    const out = {};
    for (const key of ['packetId', 'agentId']) {
        if (!(key in body))
            continue;
        const value = normalizeForeignId(body[key]);
        if (value === undefined)
            return { ok: false, error: `${key} 必须是非负整数或 null` };
        out[key] = value;
    }
    if ('groupId' in body) {
        if (typeof body.groupId !== 'string')
            return { ok: false, error: 'groupId 必须是字符串' };
        const g = body.groupId.trim();
        if (g && (g.length > 64 || !/^[A-Za-z0-9_-]+$/.test(g)))
            return { ok: false, error: 'groupId 只允许字母、数字与 -_，长度 ≤ 64' };
        out.groupId = g;
    }
    if ('landingTemplate' in body) {
        if (typeof body.landingTemplate !== 'string')
            return { ok: false, error: 'landingTemplate 必须是字符串' };
        const t = body.landingTemplate.trim();
        // 写入期就挡住非法值：否则它会在读取期被静默回退成默认模板（P-1 形态）
        if (t && !KNOWN_TEMPLATES.includes(t))
            return { ok: false, error: `landingTemplate 不在已知模板集内（须为裸名，如 japapp；已知 ${KNOWN_TEMPLATES.length} 个）` };
        out.landingTemplate = t;
    }
    return { ok: true, value: out };
}

/** GET /api/channels/:code 的绑定视图 */
function buildBindingView(doc) {
    return {
        groupId: doc.groupId || null,
        packetId: doc.packetId ?? null,
        agentId: doc.agentId ?? null,
        landingTemplate: doc.landingTemplate || null,
        // ★ 只回【外键】，不回 packet/agent 的名称：Node 无 MariaDB 客户端，
        //   且 Go 未向 Node 暴露 packet/agent 的只读端点 ⇒ 名称在本进程内不可得。
        //   不得用猜测值填充（不许把"看起来通了"当"通了"）。
        nameResolved: false,
        nameResolvedNote: '仅返回绑定外键；packet/agent 名称需 Node↔Go 只读通道（当前不存在）',
    };
}

const PASSWORD_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
const USERNAME_PREFIX_LENGTHS = [8, 10, 12];
function generatePassword(length = 12) {
    let value = '';
    for (let i = 0; i < length; i += 1) {
        value += PASSWORD_CHARS[crypto.randomInt(PASSWORD_CHARS.length)];
    }
    return value;
}
async function findAvailableChannelUsername(code) {
    for (const length of USERNAME_PREFIX_LENGTHS) {
        const username = `ch_${code.slice(0, length)}`;
        const exists = await User.findOne({ username });
        if (!exists)
            return username;
    }
    throw new Error('Username exists');
}
async function createLinkedChannelUser(input) {
    if (!input.roleId)
        throw new Error('Role not found');
    const role = await Role.findById(input.roleId);
    if (!role)
        throw new Error('Role not found');
    const username = await findAvailableChannelUsername(input.channelCode);
    const password = generatePassword();
    await User.create({
        username,
        passwordHash: await bcrypt.hash(password, 10),
        role: 'user',
        roleId: input.roleId,
        channelCodes: [input.channelCode],
    });
    return { username, password, roleId: input.roleId };
}
export async function channelsRoute(fastify) {
    const adminLikeOnly = async (request, reply) => {
        if (!isAdminLike(request.user?.role)) {
            reply.code(403);
            return reply.send({ error: 'Admin only' });
        }
    };
    fastify.get('/api/channels/options', { preHandler: adminLikeOnly }, async () => {
        const channels = await Channel.find({}, { code: 1, name: 1 }).sort({ createdAt: -1 }).lean();
        return { data: channels };
    });
    fastify.get('/api/channels', async (request) => {
        const { page = '1', pageSize = '10', keyword, domain } = request.query;
        const pageNum = Math.max(1, parseInt(page, 10) || 1);
        const size = Math.max(1, parseInt(pageSize, 10) || 10);
        const skip = (pageNum - 1) * size;
        const conditions = [];
        if (keyword)
            conditions.push({ code: keyword });
        if (domain)
            conditions.push({ domains: { $regex: domain, $options: 'i' } });
        const scope = buildChannelScopeFilter(request);
        if (Object.keys(scope).length > 0)
            conditions.push(scope);
        const filter = conditions.length > 0 ? { $and: conditions } : {};
        const [channels, total] = await Promise.all([
            Channel.find(filter).sort({ createdAt: -1 }).skip(skip).limit(size),
            Channel.countDocuments(filter),
        ]);
        return { data: channels, total, page: pageNum };
    });
    fastify.get('/api/channels/:code', async (request, reply) => {
        const { code } = request.params;
        const scope = buildChannelScopeFilter(request);
        // 越权与不存在一律 404：不向无权者泄露某个渠道码是否存在
        const channel = await Channel.findOne(scopedQuery(scope, { code }));
        if (!channel) {
            reply.code(404);
            return { error: 'Not found' };
        }
        const deviceCount = await Device.countDocuments({ channelCode: code });
        return { data: { ...channel.toObject(), deviceCount, binding: buildBindingView(channel) } };
    });
    fastify.post('/api/channels', { preHandler: adminLikeOnly }, async (request, reply) => {
        const body = request.body || {};
        const { name, seed, createUser, roleId } = body;
        if (await Channel.findOne({ name })) {
            reply.code(409);
            return { error: 'Name exists' };
        }
        // 先校验绑定字段：非法值必须在跑创建（生成 zip / 加密载荷）之前就挡掉
        const binding = normalizeBinding(body);
        if (!binding.ok) {
            reply.code(400);
            return { error: binding.error };
        }
        const result = await createChannel({ name, seed });
        if (Object.keys(binding.value).length > 0) {
            await Channel.updateOne({ code: result.code }, { $set: binding.value });
        }
        if (createUser) {
            try {
                result.createdUser = await createLinkedChannelUser({ channelCode: result.code, roleId });
            }
            catch (err) {
                const message = err instanceof Error ? err.message : String(err);
                result.userCreationError = message;
                logger.warn({ err, channelCode: result.code, roleId, operator: request.user?.username }, 'Channel user creation failed');
            }
        }
        const created = await Channel.findOne({ code: result.code });
        return { data: { ...result, binding: buildBindingView(created || result) } };
    });
    // ★ W-AD-01 1.2 的「U」：改绑定（卡片要求 CRUD 支持 packetId/agentId）。
    //   与 POST/DELETE 同属 /api/channels 资源，故用同资源的 PATCH，而非新建平行路由。
    fastify.patch('/api/channels/:code', { preHandler: adminLikeOnly }, async (request, reply) => {
        const { code } = request.params;
        const channel = await Channel.findOne({ code });
        if (!channel) {
            reply.code(404);
            return { error: 'Channel not found' };
        }
        const binding = normalizeBinding(request.body || {});
        if (!binding.ok) {
            reply.code(400);
            return { error: binding.error };
        }
        if (Object.keys(binding.value).length === 0) {
            reply.code(400);
            return { error: '请求体未含任何绑定字段（groupId/packetId/agentId/landingTemplate）' };
        }
        await Channel.updateOne({ code }, { $set: binding.value });
        const updated = await Channel.findOne({ code });
        return { data: { ...updated.toObject(), binding: buildBindingView(updated) } };
    });
    fastify.delete('/api/channels/:code', { preHandler: adminLikeOnly }, async (request, reply) => {
        const { code } = request.params;
        const channel = await Channel.findOne({ code });
        if (!channel) {
            reply.code(404);
            return { error: 'Channel not found' };
        }
        const count = await Device.countDocuments({ channelCode: code });
        if (count > 0) {
            reply.code(409);
            return { error: `Cannot delete: ${count} devices associated` };
        }
        await Channel.deleteOne({ code });
        // 删除关联用户（仅当该用户只关联此渠道时）
        try {
            const linkedUser = await User.findOne({ channelCodes: code });
            if (linkedUser) {
                if (linkedUser.channelCodes.length === 1) {
                    await User.deleteOne({ _id: linkedUser._id });
                    logger.info({ code, username: linkedUser.username }, 'Linked user deleted');
                }
                else {
                    // 用户关联多个渠道，仅移除当前渠道
                    await User.updateOne({ _id: linkedUser._id }, { $pull: { channelCodes: code } });
                    logger.info({ code, username: linkedUser.username }, 'Channel removed from user');
                }
            }
        }
        catch (err) {
            logger.warn({ err, code }, 'Failed to clean up linked user');
        }
        // 删除渠道文件（zip + corepayload.js）
        const config = loadConfig();
        const channelDir = path.join(config.storageRoot, 'channels', channel.name);
        try {
            await rm(channelDir, { recursive: true, force: true });
            logger.info({ code, channelName: channel.name, channelDir }, 'Channel files deleted');
        }
        catch (err) {
            logger.warn({ err, code, channelName: channel.name, channelDir }, 'Failed to delete channel files');
        }
        return { success: true };
    });
    fastify.get('/api/download/channel/:code', async (request, reply) => {
        const { code } = request.params;
        const user = request.user;
        if (!user) {
            reply.code(401);
            return { error: 'Not logged in' };
        }
        // 非管理员只能下载自己的渠道
        if (!isAdminLike(user.role)) {
            const userDoc = await User.findById(user.userId);
            if (!userDoc || !userDoc.channelCodes || !userDoc.channelCodes.includes(code)) {
                reply.code(403);
                return { error: 'No permission' };
            }
        }
        const channel = await Channel.findOne({ code });
        if (!channel) {
            reply.code(404);
            return { error: 'Not found' };
        }
        const config = loadConfig();
        const zipPath = path.join(config.storageRoot, `channels/${channel.name}/${channel.code}.zip`);
        try {
            const fileStat = await stat(zipPath);
            reply.header('Content-Type', 'application/zip');
            reply.header('Content-Disposition', `attachment; filename="${channel.code}.zip"`);
            reply.header('Content-Length', fileStat.size);
            return reply.send(createReadStream(zipPath));
        }
        catch (err) {
            logger.warn({ err, zipPath }, 'Channel zip file not accessible');
            reply.code(404);
            return { error: 'Zip file not found' };
        }
    });
    // Regenerate channel zip
    fastify.post('/api/channels/:code/regenerate', async (request, reply) => {
        if (!request.user || !isAdminLike(request.user.role)) {
            reply.code(403);
            return { error: 'Admin only' };
        }
        const { code } = request.params;
        try {
            await regenerateChannelZip(code);
            return { success: true };
        }
        catch (err) {
            logger.error({ err, code }, 'Channel zip regeneration failed');
            reply.code(500);
            return { error: err.message || 'Regeneration failed' };
        }
    });
}
//# sourceMappingURL=channels.js.map