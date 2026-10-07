import fp from 'fastify-plugin';
import jwt from 'jsonwebtoken';
import { loadConfig } from '../../../config/index.js';
import { logger, logAls } from '../../../core/logger/index.js';
import { findMenuKeyByPath } from '../../../config/menus.js';
import { getRealIP } from '../../../core/utils/ip.js';
import { getRedis } from '../../../core/db/connection.js';
import { getAuthContext } from '../../../core/auth/context.js';
import { isAdminLike } from '../../../core/auth/permissions.js';
const SKIP_AUTH_PATHS = ['/api/auth/login', '/api/auth/refresh', '/api/auth/totp/complete-login', '/api/auth/register', '/api/tatum/webhook'];
export const authMiddleware = fp(async function authMiddleware(fastify) {
    fastify.decorateRequest('channelFilter', null);
    fastify.decorateRequest('chainFilter', null);
    fastify.decorateRequest('visibleSocialTypes', null);
    fastify.addHook('preHandler', async (request, reply) => {
        const urlPath = request.url.split('?')[0];
        if (SKIP_AUTH_PATHS.includes(urlPath))
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