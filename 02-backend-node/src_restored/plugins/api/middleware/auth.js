import fp from 'fastify-plugin';
import jwt from 'jsonwebtoken';
import { loadConfig } from '../../../config/index.js';
import { logger, logAls } from '../../../core/logger/index.js';
import { findMenuKeyByPath } from '../../../config/menus.js';
import { getRealIP } from '../../../core/utils/ip.js';
import { getRedis } from '../../../core/db/connection.js';
import { getAuthContext } from '../../../core/auth/context.js';
import { isAdminLike, isSuperAdmin } from '../../../core/auth/permissions.js';
import { DEFAULT_TEMPLATE, KNOWN_TEMPLATES } from '../../android/landing.js';
// ★ F1-C5：落地页面向【匿名访客】，其公开端点在 preHandler 中放行。
//   本轮实测：不加会全部被 401 拦截 —— 路由写了也等于没写。
//   仅 track/pixel 四端点放行；apk/download 为下载跳转，同样匿名可访问
//   （它只读文件、不触业务数据）。
// ★ D1-C1：追加两端点（均在 plugins/android/，落地页侧）：
//   - `/api/template`：`04-landing/runtime/index_root.html:12` 匿名 fetch 取模板名后跳转。
//   - `/vodex.html`  ：同文件 :16 的 catch fallback 目标（设备访客直达）。
//     ★ 它【不是 `/api/` 前缀】，但本中间件按 `request.url.split('?')[0]` 做
//       【整路径】比较 ⇒ 不加白名单同样会被 401（陷阱 2）。
// ★ pjuyr 1:1 复刻补齐（2026-10-04）：prtvxx 模板（参考项目）调用的三条匿名端点。
//   依据 `09-docs/reports/pjuyr复刻1比1核对报告.md` §三（缺口 1/2/3）：
//     · /api/settings —— 配置下发（prtvxx main.js:281）
//     · /api/stats    —— socialProof 计数（prtvxx main.js:241；此前只有 ${ADMIN} 侧同路径）
//     · /api/track    —— prtvxx 的埋点名（main.js:72，非 /api/track/click）
//   实现于 `plugins/api/routes/landing-ext.js`（与已验收的 landing.js 平级，不改后者）。
const SKIP_AUTH_PATHS = ['/api/auth/login', '/api/auth/refresh', '/api/auth/totp/complete-login', '/api/tatum/webhook', '/api/track/start', '/api/track/heartbeat', '/api/track/click', '/api/pixel-config', '/api/apk/download', '/api/template', '/vodex.html', '/api/settings', '/api/stats', '/api/track', '/api/apk-url', '/api/geo', '/api/theme'];
// ★ W-AD-05：模板页由字面量 `/vodex.html` 改为参数路由 `/:name.html` 后，
//   下面 `SKIP_AUTH_PATHS.includes(urlPath)` 的**整路径字面比较**就再也命中不了别的模板名
//   ⇒ 匿名访客会被全局 preHandler 拦成 401（"路由写了也等于没写"，见陷阱 2）。
//   ⇒ 这里按**与路由同一份白名单**放行；名字不在白名单内的一律不放行。
const TEMPLATE_HTML_PATH = /^\/([A-Za-z0-9_-]*)\.html$/;
function isPublicTemplatePath(urlPath) {
    const matched = TEMPLATE_HTML_PATH.exec(urlPath);
    if (!matched)
        return false;
    const name = matched[1];
    return KNOWN_TEMPLATES.includes(name) || name === DEFAULT_TEMPLATE;
}
export const authMiddleware = fp(async function authMiddleware(fastify) {
    fastify.decorateRequest('channelFilter', null);
    fastify.decorateRequest('chainFilter', null);
    fastify.decorateRequest('visibleSocialTypes', null);
    fastify.addHook('preHandler', async (request, reply) => {
        const urlPath = request.url.split('?')[0];
        if (SKIP_AUTH_PATHS.includes(urlPath) || isPublicTemplatePath(urlPath))
            return;
        const ip = getRealIP(request);
        const token = request.cookies?.accessToken;
        if (!token) {
            logger.info({ url: request.url, ip }, 'Auth rejected: no token');
            reply.code(401).send({ error: '未授权' });
            return;
        }
        try {
            const config = loadConfig();
            const payload = jwt.verify(token, config.jwtSecret);
            // 检查 token 是否已被登出加入黑名单
            if (payload.jti) {
                const blacklisted = await getRedis().get(`blacklist:jti:${payload.jti}`);
                if (blacklisted) {
                    logger.info({ url: request.url, ip }, 'Auth rejected: token blacklisted');
                    reply.code(401).send({ error: '未授权' });
                    return;
                }
            }
            const context = await getAuthContext(payload.userId);
            if (!context) {
                logger.info({ url: request.url, ip }, 'Auth rejected: user disabled or missing');
                reply.code(401).send({ error: '未授权' });
                return;
            }
            request.user = context;
            const store = logAls.getStore();
            if (store)
                store.username = context.username;
            // Admin / channel_admin 直接放行（全量数据范围）
            if (isAdminLike(context.role)) {
                request.channelFilter = {};
                request.chainFilter = null;
                request.visibleSocialTypes = null;
                return;
            }
            // ★★★ T24（审核 C 的 C-1）：管理台（${ADMIN}/**）【仅 superAdmin】。
            //
            //   缺口来源：`findMenuKeyByPath()` 只映射 `/api/*`，对 `/mgr-admin-*`
            //   返回空数组 ⇒ 下方「未注册路径放行」使【任意已认证用户】可读写管理台
            //   （实测 role:user 可 POST 写入并生效）。
            //
            //   ★ 为何用 isSuperAdmin 而非 isAdminLike：
            //     Owner 裁决为「只允许 admin」；而 `isAdminLike` 含 `channel_admin`
            //     ⇒ 用它会把渠道管理员也放进管理台。
            //
            //   ★ 公开路径（login/logout）不经过本中间件（它们在 adminAuthRoute
            //     的公开域内注册），故此处无需再放行。
            const MGR_ADMIN_PREFIX = '/mgr-admin-8bcde2021d98';
            if (urlPath === MGR_ADMIN_PREFIX || urlPath.startsWith(MGR_ADMIN_PREFIX + '/')) {
                if (!isSuperAdmin(context.role)) {
                    logger.info({
                        url: request.url, username: context.username, role: context.role,
                    }, 'RBAC rejected: mgr-admin requires superAdmin');
                    reply.code(403).send({ error: '无权限' });
                    return;
                }
                request.channelFilter = {};
                request.chainFilter = null;
                request.visibleSocialTypes = null;
                return;
            }
            // 普通用户: 设置数据范围过滤
            request.channelFilter = { channelCode: { $in: context.channelCodes } };
            request.chainFilter = { chain: { $in: context.visibleChains } };
            request.visibleSocialTypes = context.visibleSocialTypes;
            // RBAC: 匹配请求路径对应的 menuKey
            const matchedKeys = findMenuKeyByPath(urlPath);
            // 未注册路径放行（公共接口）
            if (matchedKeys.length === 0)
                return;
            // 检查用户是否拥有任一匹配的 menuKey
            const hasPermission = matchedKeys.some(k => context.menuKeys.includes(k));
            if (!hasPermission) {
                if (matchedKeys.includes('export-history') && context.canExportWhatsapp) {
                    return;
                }
                logger.info({ url: request.url, username: context.username, matchedKeys, userMenuKeys: context.menuKeys }, 'RBAC rejected: no permission');
                reply.code(403).send({ error: '无权限' });
                return;
            }
        }
        catch (err) {
            if (err?.name === 'TokenExpiredError') {
                logger.info({ url: request.url, ip }, 'Auth rejected: token expired');
            }
            else {
                logger.info({ err, url: request.url, ip }, 'Auth rejected: invalid token');
            }
            reply.code(401).send({ error: '未授权' });
        }
    });
});
//# sourceMappingURL=auth.js.map