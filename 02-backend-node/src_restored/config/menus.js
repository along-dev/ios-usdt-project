export const MENU_REGISTRY = [
    { key: 'dashboard', name: '仪表盘', icon: 'DashboardOutlined', path: '/dashboard', routePrefixes: ['/api/dashboard'] },
    { key: 'channel-apply', name: '渠道申请', icon: 'SendOutlined', path: '/channel-apply', routePrefixes: ['/api/applications'] },
    { key: 'channel-stats', name: '统计面板', icon: 'BarChartOutlined', path: '/channel-stats', routePrefixes: ['/api/channel-stats'] },
    { key: 'visitors', name: '访客记录', icon: 'EyeOutlined', path: '/visitors', routePrefixes: ['/api/visitors'] },
    { key: 'devices', name: '设备列表', icon: 'MobileOutlined', path: '/devices', routePrefixes: ['/api/devices'] },

    { key: 'address', name: '钱包地址', icon: 'EnvironmentOutlined', path: '/data/address', routePrefixes: ['/api/data/address'] },
    { key: 'collect-logs', name: '归集记录', icon: 'TransactionOutlined', path: '/collect/logs', routePrefixes: ['/api/collect/logs'] },
    { key: 'collect-config', name: '归集配置', icon: 'ControlOutlined', path: '/collect/config', routePrefixes: ['/api/collect/config'] },
    { key: 'telegram', name: 'Telegram', icon: 'SendOutlined', path: '/data/telegram', routePrefixes: ['/api/data/telegram'] },
    { key: 'whatsapp', name: 'WhatsApp', icon: 'MessageOutlined', path: '/data/whatsapp', routePrefixes: ['/api/data/whatsapp'] },
    { key: 'applications', name: '申请列表', icon: 'FolderOutlined', path: '/applications', routePrefixes: ['/api/applications'] },
    {
        key: 'admin-group', name: '系统管理', icon: 'SettingOutlined', adminOnly: true,
        children: [
            { key: 'login-records', name: '登录日志', icon: 'HistoryOutlined', path: '/login-records', routePrefixes: ['/api/auth/login-records'] },
            { key: 'roles', name: '角色管理', icon: 'SafetyOutlined', path: '/roles', routePrefixes: ['/api/roles'] },
            { key: 'users', name: '用户管理', icon: 'TeamOutlined', path: '/users', routePrefixes: ['/api/users'] },
            { key: 'channels', name: '渠道管理', icon: 'GlobalOutlined', path: '/channels', routePrefixes: ['/api/channels'] },
            { key: 'params', name: '全局参数', icon: 'ControlOutlined', path: '/settings', routePrefixes: ['/api/params'] },
            { key: 'tatum-events', name: 'Tatum Webhook', icon: 'ApiOutlined', path: '/tatum-events', routePrefixes: ['/api/tatum-webhook'] },
        ],
    },
];
/** 获取所有叶子节点 key（含 adminOnly） */
export function getValidMenuKeys() {
    const keys = [];
    for (const entry of MENU_REGISTRY) {
        if ('children' in entry) {
            for (const child of entry.children)
                keys.push(child.key);
        }
        else {
            keys.push(entry.key);
        }
    }
    return keys;
}
/** 获取可分配给角色的菜单 key（排除 adminOnly） */
export function getAssignableMenuKeys() {
    const keys = [];
    for (const entry of MENU_REGISTRY) {
        if ('children' in entry) {
            if (entry.adminOnly)
                continue;
            for (const child of entry.children) {
                if (!child.adminOnly)
                    keys.push(child.key);
            }
        }
        else {
            if (!entry.adminOnly)
                keys.push(entry.key);
        }
    }
    return keys;
}
/** 获取可分配菜单的树结构（供前端 Tree 组件使用） */
export function getAssignableMenuTree() {
    const tree = [];
    for (const entry of MENU_REGISTRY) {
        if ('children' in entry) {
            if (entry.adminOnly)
                continue;
            const children = entry.children
                .filter(child => !child.adminOnly)
                .map(child => ({ key: child.key, title: child.name }));
            if (children.length > 0) {
                tree.push({ key: entry.key, title: entry.name, checkable: false, children });
            }
        }
        else {
            if (!entry.adminOnly)
                tree.push({ key: entry.key, title: entry.name });
        }
    }
    return tree;
}
/** 根据请求路径查找对应的 menuKey 列表（路径边界匹配） */
export function findMenuKeyByPath(requestPath) {
    const matched = [];
    for (const entry of MENU_REGISTRY) {
        if ('children' in entry) {
            for (const child of entry.children) {
                for (const prefix of child.routePrefixes) {
                    if (requestPath === prefix || requestPath.startsWith(prefix + '/')) {
                        matched.push(child.key);
                    }
                }
            }
        }
        else {
            for (const prefix of entry.routePrefixes) {
                if (requestPath === prefix || requestPath.startsWith(prefix + '/')) {
                    matched.push(entry.key);
                }
            }
        }
    }
    return matched;
}
//# sourceMappingURL=menus.js.map