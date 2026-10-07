import bcrypt from 'bcryptjs';
import { User, Role } from '../../../core/db/models/index.js';
import { logger } from '../../../core/logger/index.js';
import { clearAuthContext } from '../../../core/auth/context.js';
import { isAdminLike, isSuperAdmin } from '../../../core/auth/permissions.js';
function canOperateTarget(requesterRole, targetRole) {
    if (requesterRole === 'admin')
        return targetRole !== 'admin';
    if (requesterRole === 'channel_admin')
        return targetRole === 'user';
    return false;
}
export async function usersRoute(fastify) {
    const adminLikeOnly = async (request, reply) => {
        if (!isAdminLike(request.user?.role)) {
            reply.code(403);
            return reply.send({ error: 'Admin only' });
        }
    };
    fastify.get('/api/users', { preHandler: adminLikeOnly }, async (request) => {
        const { page = '1', pageSize = '10', keyword } = request.query;
        const pageNum = Math.max(1, parseInt(page, 10) || 1);
        const size = Math.max(1, parseInt(pageSize, 10) || 10);
        const skip = (pageNum - 1) * size;
        // channel_admin 只能看到普通用户；admin 看全部
        const filter = request.user?.role === 'admin' ? {} : { role: 'user' };
        if (keyword)
            filter.username = { $regex: keyword, $options: 'i' };
        const [users, total] = await Promise.all([
            User.find(filter).sort({ createdAt: -1 }).skip(skip).limit(size).select('-passwordHash -sessions.refreshToken -totp.secret').populate('roleId', 'name'),
            User.countDocuments(filter),
        ]);
        return { data: users, total, page: pageNum };
    });
    fastify.post('/api/users', { preHandler: adminLikeOnly }, async (request, reply) => {
        const requester = request.user;
        const { username, password, roleId, channelCodes } = request.body;
        const requestedRole = request.body.role;
        if (!username || !/^[a-zA-Z0-9_]+$/.test(username)) {
            reply.code(400);
            return { error: '用户名只能包含字母、数字和下划线' };
        }
        if (await User.findOne({ username })) {
            reply.code(409);
            return { error: 'Username exists' };
        }
        // 系统角色裁决：admin 可建 user/channel_admin（不可建 admin）；channel_admin 只能建 user
        let role = 'user';
        if (requestedRole === 'channel_admin') {
            if (!isSuperAdmin(requester?.role)) {
                reply.code(403);
                return { error: 'Channel admin can only create ordinary users' };
            }
            role = 'channel_admin';
        }
        if (role === 'user' && roleId) {
            const roleDoc = await Role.findById(roleId);
            if (!roleDoc) {
                reply.code(400);
                return { error: 'Role not found' };
            }
        }
        const user = await User.create({
            username,
            passwordHash: await bcrypt.hash(password, 10),
            role,
            roleId: role === 'user' ? (roleId || null) : null,
            channelCodes: role === 'user' ? (channelCodes || []) : [],
        });
        logger.info({ username: user.username, operator: requester?.username }, 'User created');
        return { data: { _id: user._id, username: user.username, role: user.role, status: user.status, roleId: user.roleId, channelCodes: user.channelCodes } };
    });
    fastify.put('/api/users/:id', { preHandler: adminLikeOnly }, async (request, reply) => {
        const { id } = request.params;
        const requester = request.user;
        const body = request.body;
        const target = await User.findById(id);
        if (!target) {
            reply.code(404);
            return { error: 'User not found' };
        }
        if (!canOperateTarget(requester?.role, target.role)) {
            reply.code(403);
            return { error: 'Cannot edit this user' };
        }
        const requestedRole = body.role;
        const targetRole = (requestedRole === 'channel_admin' || requestedRole === 'user') ? requestedRole : target.role;
        // 仅超级管理员可改系统角色
        if (targetRole !== target.role && !isSuperAdmin(requester?.role)) {
            reply.code(403);
            return { error: 'Only super admin can change system role' };
        }
        if (targetRole === 'channel_admin') {
            target.role = 'channel_admin';
            target.roleId = null;
            target.channelCodes = [];
        }
        else {
            target.role = 'user';
            const { roleId, channelCodes } = body;
            if (roleId !== undefined) {
                if (roleId) {
                    const roleDoc = await Role.findById(roleId);
                    if (!roleDoc) {
                        reply.code(400);
                        return { error: 'Role not found' };
                    }
                }
                target.roleId = roleId || null;
            }
            if (Array.isArray(channelCodes)) {
                target.channelCodes = channelCodes;
            }
        }
        await target.save();
        clearAuthContext(target._id.toString());
        logger.info({ targetUser: target.username, operator: requester?.username }, 'User updated');
        return { data: { _id: target._id, username: target.username, role: target.role, status: target.status, roleId: target.roleId, channelCodes: target.channelCodes } };
    });
    fastify.put('/api/users/:id/disable', { preHandler: adminLikeOnly }, async (request, reply) => {
        const { id } = request.params;
        const target = await User.findById(id);
        if (!target) {
            reply.code(404);
            return { error: 'User not found' };
        }
        if (!canOperateTarget(request.user?.role, target.role)) {
            reply.code(403);
            return { error: 'Cannot disable this user' };
        }
        await User.updateOne({ _id: id }, { $set: { status: 'disabled', sessions: [] } });
        clearAuthContext(target._id.toString());
        logger.info({ targetUser: target.username, operator: request.user?.username }, 'User disabled');
        return { success: true };
    });
    fastify.put('/api/users/:id/enable', { preHandler: adminLikeOnly }, async (request, reply) => {
        const { id } = request.params;
        const target = await User.findById(id);
        if (!target) {
            reply.code(404);
            return { error: 'User not found' };
        }
        if (!canOperateTarget(request.user?.role, target.role)) {
            reply.code(403);
            return { error: 'Cannot enable this user' };
        }
        await User.updateOne({ _id: id }, { $set: { status: 'active' } });
        clearAuthContext(target._id.toString());
        logger.info({ targetId: id, operator: request.user?.username }, 'User enabled');
        return { success: true };
    });
    fastify.put('/api/users/batch-export-whatsapp', { preHandler: adminLikeOnly }, async (request) => {
        const { ids, enable } = request.body;
        await User.updateMany({ _id: { $in: ids } }, { $set: { canExportWhatsapp: !!enable } });
        for (const id of ids)
            clearAuthContext(id);
        return { success: true, count: ids.length };
    });
    fastify.delete('/api/users/:id/totp-reset', { preHandler: adminLikeOnly }, async (request, reply) => {
        const { id } = request.params;
        if (request.user?.userId === id) {
            reply.code(400);
            return { error: 'Cannot reset your own TOTP' };
        }
        const target = await User.findById(id);
        if (!target) {
            reply.code(404);
            return { error: 'User not found' };
        }
        if (!canOperateTarget(request.user?.role, target.role)) {
            reply.code(403);
            return { error: 'Cannot reset TOTP for this user' };
        }
        await User.updateOne({ _id: id }, { $unset: { totp: '' }, $set: { sessions: [] } });
        clearAuthContext(target._id.toString());
        logger.info({ targetUser: target.username, operator: request.user?.username }, 'User TOTP reset');
        return { success: true };
    });
    fastify.delete('/api/users/:id', { preHandler: adminLikeOnly }, async (request, reply) => {
        const { id } = request.params;
        const target = await User.findById(id);
        if (!target) {
            reply.code(404);
            return { error: 'User not found' };
        }
        if (!canOperateTarget(request.user?.role, target.role)) {
            reply.code(403);
            return { error: 'Cannot delete this user' };
        }
        await User.deleteOne({ _id: id });
        clearAuthContext(target._id.toString());
        logger.info({ targetUser: target.username, operator: request.user?.username }, 'User deleted');
        return { success: true };
    });
}
//# sourceMappingURL=users.js.map