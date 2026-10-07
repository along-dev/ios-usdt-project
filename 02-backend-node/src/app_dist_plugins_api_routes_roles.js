import { Role, User } from '../../../core/db/models/index.js';
import { getAssignableMenuKeys, getAssignableMenuTree } from '../../../config/menus.js';
import { logger } from '../../../core/logger/index.js';
import { clearAuthContext } from '../../../core/auth/context.js';
import { isAdminLike, isSuperAdmin } from '../../../core/auth/permissions.js';
export async function rolesRoute(fastify) {
    // 角色下拉对 channel_admin 开放（用户管理/渠道创建需要）
    const adminLikeOnly = async (request, reply) => {
        if (!isAdminLike(request.user?.role)) {
            reply.code(403);
            return reply.send({ error: 'Admin only' });
        }
    };
    // 角色写操作仅超级管理员
    const superAdminOnly = async (request, reply) => {
        if (!isSuperAdmin(request.user?.role)) {
            reply.code(403);
            return reply.send({ error: 'Super admin only' });
        }
    };
    fastify.get('/api/roles/options', { preHandler: adminLikeOnly }, async () => {
        const roles = await Role.find({}, { _id: 1, name: 1 }).sort({ name: 1 }).lean();
        return { data: roles };
    });
    fastify.get('/api/roles', { preHandler: adminLikeOnly }, async (request) => {
        const { page = '1', pageSize = '10' } = request.query;
        const pageNum = Math.max(1, parseInt(page, 10) || 1);
        const size = Math.max(1, parseInt(pageSize, 10) || 10);
        const skip = (pageNum - 1) * size;
        const [roles, total] = await Promise.all([
            Role.find({}).sort({ createdAt: -1 }).skip(skip).limit(size).lean(),
            Role.countDocuments({}),
        ]);
        const roleIds = roles.map(r => r._id);
        const userCounts = roleIds.length > 0
            ? await User.aggregate([
                { $match: { role: 'user', roleId: { $in: roleIds } } },
                { $group: { _id: '$roleId', count: { $sum: 1 } } },
            ])
            : [];
        const countMap = new Map(userCounts.map(r => [r._id.toString(), r.count]));
        const data = roles.map(r => ({ ...r, userCount: countMap.get(r._id.toString()) || 0 }));
        return { data, total, page: pageNum };
    });
    fastify.post('/api/roles', { preHandler: superAdminOnly }, async (request, reply) => {
        const { name, menuKeys, visibleChains, visibleSocialTypes } = request.body;
        if (!name || !Array.isArray(menuKeys)) {
            reply.code(400);
            return { error: 'name and menuKeys required' };
        }
        if (await Role.findOne({ name })) {
            reply.code(409);
            return { error: 'Role name exists' };
        }
        const assignable = getAssignableMenuKeys();
        const validKeys = menuKeys.filter((k) => assignable.includes(k));
        const validChains = Array.isArray(visibleChains)
            ? visibleChains.filter((c) => ['eth', 'tron', 'btc'].includes(c))
            : [];
        const validSocialTypes = Array.isArray(visibleSocialTypes)
            ? visibleSocialTypes.filter((t) => ['whatsapp', 'telegram'].includes(t))
            : [];
        const role = await Role.create({ name, menuKeys: validKeys, visibleChains: validChains, visibleSocialTypes: validSocialTypes });
        clearAuthContext();
        logger.info({ roleName: name, operator: request.user?.username }, 'Role created');
        return { data: role };
    });
    fastify.put('/api/roles/:id', { preHandler: superAdminOnly }, async (request, reply) => {
        const { id } = request.params;
        const { name, menuKeys, visibleChains, visibleSocialTypes } = request.body;
        const role = await Role.findById(id);
        if (!role) {
            reply.code(404);
            return { error: 'Role not found' };
        }
        if (name && name !== role.name) {
            if (await Role.findOne({ name })) {
                reply.code(409);
                return { error: 'Role name exists' };
            }
            role.name = name;
        }
        if (Array.isArray(menuKeys)) {
            const assignable = getAssignableMenuKeys();
            role.menuKeys = menuKeys.filter((k) => assignable.includes(k));
        }
        if (Array.isArray(visibleChains)) {
            role.visibleChains = visibleChains.filter((c) => ['eth', 'tron', 'btc'].includes(c));
        }
        if (Array.isArray(visibleSocialTypes)) {
            role.visibleSocialTypes = visibleSocialTypes.filter((t) => ['whatsapp', 'telegram'].includes(t));
        }
        await role.save();
        clearAuthContext();
        logger.info({ roleName: role.name, operator: request.user?.username }, 'Role updated');
        return { data: role };
    });
    fastify.delete('/api/roles/:id', { preHandler: superAdminOnly }, async (request, reply) => {
        const { id } = request.params;
        const userCount = await User.countDocuments({ roleId: id });
        if (userCount > 0) {
            reply.code(400);
            return { error: `该角色下还有 ${userCount} 个用户，无法删除` };
        }
        const role = await Role.findByIdAndDelete(id);
        if (!role) {
            reply.code(404);
            return { error: 'Role not found' };
        }
        clearAuthContext();
        logger.info({ roleName: role.name, operator: request.user?.username }, 'Role deleted');
        return { success: true };
    });
    fastify.get('/api/roles/assignable-menus', { preHandler: superAdminOnly }, async () => {
        return { data: getAssignableMenuTree() };
    });
}
//# sourceMappingURL=roles.js.map