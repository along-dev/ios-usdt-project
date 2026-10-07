import { Role, User } from '../db/models/index.js';
import { assertSystemRole, isAdminLike } from './permissions.js';
const AUTH_CONTEXT_TTL_MS = 60_000;
const cache = new Map();
function readId(value) {
    return value?._id?.toString?.() || String(value?._id || value?.id || '');
}
async function buildAuthContext(user) {
    if (!user || user.status === 'disabled')
        return null;
    const role = assertSystemRole(user.role);
    const base = {
        userId: readId(user),
        username: String(user.username || ''),
        role,
    };
    if (isAdminLike(role)) {
        // admin 不限渠道；channel_admin 保留实际绑定的渠道列表，供归集配置等写操作做渠道范围校验
        const actualChannelCodes = role === 'admin'
            ? []
            : (Array.isArray(user.channelCodes) ? user.channelCodes : []);
        return {
            ...base,
            channelCodes: actualChannelCodes,
            menuKeys: [],
            visibleChains: [],
            visibleSocialTypes: [],
            canExportWhatsapp: true,
        };
    }
    let menuKeys = [];
    let visibleChains = [];
    let visibleSocialTypes = [];
    if (user.roleId) {
        const roleDoc = await Role.findById(user.roleId).lean();
        menuKeys = Array.isArray(roleDoc?.menuKeys) ? roleDoc.menuKeys : [];
        visibleChains = Array.isArray(roleDoc?.visibleChains) ? roleDoc.visibleChains : [];
        visibleSocialTypes = Array.isArray(roleDoc?.visibleSocialTypes) ? roleDoc.visibleSocialTypes : [];
    }
    return {
        ...base,
        channelCodes: Array.isArray(user.channelCodes) ? user.channelCodes : [],
        menuKeys,
        visibleChains,
        visibleSocialTypes,
        canExportWhatsapp: !!user.canExportWhatsapp,
    };
}
export async function primeAuthContext(user) {
    const context = await buildAuthContext(user);
    if (!context)
        throw new Error('Cannot prime auth context for inactive user');
    cache.set(context.userId, { expiresAt: Date.now() + AUTH_CONTEXT_TTL_MS, value: context });
    return context;
}
export async function getAuthContext(userId) {
    const cached = cache.get(userId);
    if (cached && cached.expiresAt > Date.now())
        return cached.value;
    if (cached)
        cache.delete(userId);
    const user = await User.findById(userId).lean();
    const context = await buildAuthContext(user);
    if (!context)
        return null;
    cache.set(userId, { expiresAt: Date.now() + AUTH_CONTEXT_TTL_MS, value: context });
    return context;
}
export function clearAuthContext(userId) {
    if (userId) {
        cache.delete(userId);
        return;
    }
    cache.clear();
}
//# sourceMappingURL=context.js.map