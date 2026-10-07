export function assertSystemRole(value) {
    if (value === 'admin' || value === 'channel_admin' || value === 'user')
        return value;
    return 'user';
}
export function isSuperAdmin(role) {
    return role === 'admin';
}
export function isAdminLike(role) {
    return role === 'admin' || role === 'channel_admin';
}
//# sourceMappingURL=permissions.js.map