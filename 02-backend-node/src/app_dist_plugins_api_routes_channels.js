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
        const filter = {};
        if (keyword)
            filter.code = keyword;
        if (domain)
            filter.domains = { $regex: domain, $options: 'i' };
        const [channels, total] = await Promise.all([
            Channel.find(filter).sort({ createdAt: -1 }).skip(skip).limit(size),
            Channel.countDocuments(filter),
        ]);
        return { data: channels, total, page: pageNum };
    });
    fastify.get('/api/channels/:code', async (request, reply) => {
        const { code } = request.params;
        const channel = await Channel.findOne({ code });
        if (!channel) {
            reply.code(404);
            return { error: 'Not found' };
        }
        const deviceCount = await Device.countDocuments({ channelCode: code });
        return { data: { ...channel.toObject(), deviceCount } };
    });
    fastify.post('/api/channels', { preHandler: adminLikeOnly }, async (request, reply) => {
        const { name, seed, createUser, roleId } = request.body;
        if (await Channel.findOne({ name })) {
            reply.code(409);
            return { error: 'Name exists' };
        }
        const result = await createChannel({ name, seed });
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
        return { data: result };
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