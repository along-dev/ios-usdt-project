import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import { User, Role } from '../../../core/db/models/index.js';
import { loadConfig } from '../../../config/index.js';
import { DEFAULTS } from '../../../config/constants.js';
import { logger } from '../../../core/logger/index.js';
import { MENU_REGISTRY } from '../../../config/menus.js';
import { listLoginRecords, recordLoginEvent } from '../../../core/auth/login-records.js';
import { getRedis } from '../../../core/db/connection.js';
import { assertTotpEncryptionKey, decryptSecret, encryptSecret, generateTotp, verifyTotp } from '../../../core/crypto/totp.js';
import { clearTotpAttempts, consumePendingTotpToken, getPendingTotpCookieOptions, recordFailedTotpAttempt, signPendingTotpToken, verifyPendingTotpToken } from '../../../core/auth/pending-totp.js';
import { buildJwtPayload, getAuthCookieOptions, issueLoginSession, setLoginCookies } from '../../../core/auth/session.js';
import { primeAuthContext } from '../../../core/auth/context.js';
import { getRealIP } from '../../../core/utils/ip.js';
import { isAdminLike } from '../../../core/auth/permissions.js';
const COOKIE_OPTS = getAuthCookieOptions();
const CHANNEL_ADMIN_SYSTEM_MENU_KEYS = new Set(['users', 'channels']);
function serializeMenuItem(item) {
    return { key: item.key, name: item.name, path: item.path };
}
function buildAdminMenuTree() {
    return MENU_REGISTRY.map(entry => {
        if ('children' in entry) {
            return {
                key: entry.key,
                name: entry.name,
                icon: entry.icon,
                children: entry.children.map(serializeMenuItem),
            };
        }
        return {
            key: entry.key,
            name: entry.name,
            icon: entry.icon,
            path: entry.path,
        };
    });
}
function buildChannelAdminMenuTree() {
    const result = [];
    for (const entry of MENU_REGISTRY) {
        if ('children' in entry) {
            const group = entry;
            // 系统管理分组只保留 users/channels，其余系统项（roles/payloads/params/...）不返回
            if (group.key === 'admin-group') {
                const children = group.children
                    .filter(child => CHANNEL_ADMIN_SYSTEM_MENU_KEYS.has(child.key))
                    .map(serializeMenuItem);
                if (children.length > 0) {
                    result.push({ key: group.key, name: group.name, icon: group.icon, children });
                }
                continue;
            }
            // 业务分组表现与 admin 一致（含 collect-config/export-history 等业务型 admin 菜单）
            result.push({
                key: group.key,
                name: group.name,
                icon: group.icon,
                children: group.children.map(serializeMenuItem),
            });
            continue;
        }
        const item = entry;
        result.push({ key: item.key, name: item.name, icon: item.icon, path: item.path });
    }
    return result;
}
function buildUserMenuTree(menuKeys) {
    const result = [];
    for (const entry of MENU_REGISTRY) {
        if ('children' in entry) {
            const group = entry;
            if (group.adminOnly)
                continue;
            const children = group.children
                .filter(child => !child.adminOnly)
                .filter(child => menuKeys.includes(child.key))
                .map(serializeMenuItem);
            if (children.length > 0) {
                result.push({ key: group.key, name: group.name, icon: group.icon, children });
            }
            continue;
        }
        const item = entry;
        if (item.adminOnly)
            continue;
        if (!menuKeys.includes(item.key))
            continue;
        result.push({ key: item.key, name: item.name, icon: item.icon, path: item.path });
    }
    return result;
}
/** 根据系统角色与权限过滤菜单树 */
function buildMenuTree(userRole, menuKeys) {
    if (userRole === 'admin')
        return buildAdminMenuTree();
    if (userRole === 'channel_admin')
        return buildChannelAdminMenuTree();
    return buildUserMenuTree(menuKeys);
}
const RL_LOGIN_MAX = 10;      // 登录：15分钟内最多10次失败
const RL_LOGIN_WINDOW = 900;  // 15分钟
const RL_REGISTER_MAX = 3;    // 注册：1小时内最多3次
const RL_REGISTER_WINDOW = 3600; // 1小时

async function isRateLimited(key, maxAttempts) {
    const count = parseInt(await getRedis().get(key) || '0');
    return count >= maxAttempts;
}

async function incrRateLimit(key, windowSec) {
    const redis = getRedis();
    const count = await redis.incr(key);
    if (count === 1) {
        await redis.expire(key, windowSec);
    }
}

async function clearRateLimit(key) {
    await getRedis().del(key);
}

export async function authRoute(fastify) {
    const config = loadConfig();
    fastify.post('/api/auth/login', async (request, reply) => {
        const { username, password } = request.body;
        const ip = getRealIP(request);

        // 拒绝非字符串类型和额外字段
        if (typeof username !== 'string' || typeof password !== 'string') {
            reply.code(400);
            return { error: '请求失败' };
        }
        const allowedFields = ['username', 'password'];
        const extraFields = Object.keys(request.body).filter(k => !allowedFields.includes(k));
        if (extraFields.length > 0) {
            reply.code(400);
            return { error: '请求失败' };
        }

        // 速率限制：检查但不在此计数
        const rlKey = `ratelimit:login:${ip}`;
        if (await isRateLimited(rlKey, RL_LOGIN_MAX)) {
            reply.code(429);
            return { error: '请求过于频繁，请稍后再试' };
        }
        const user = await User.findOne({ username });
        if (!user) {
            logger.info({ username, ip }, 'Login failed: user not found');
            await incrRateLimit(rlKey, RL_LOGIN_WINDOW);
            reply.code(401);
            return { error: '用户名或密码错误' };
        }
        if (user.status === 'disabled') {
            logger.info({ username, ip }, 'Login failed: account disabled');
            await incrRateLimit(rlKey, RL_LOGIN_WINDOW);
            reply.code(403);
            return { error: '用户名或密码错误' };
        }
        const valid = await bcrypt.compare(password, user.passwordHash);
        if (!valid) {
            logger.info({ username, ip }, 'Login failed: wrong password');
            await incrRateLimit(rlKey, RL_LOGIN_WINDOW);
            reply.code(401);
            return { error: '用户名或密码错误' };
        }
        const loginMetadata = {
            userId: user._id.toString(),
            username: user.username,
            role: user.role,
            ip,
            deviceInfo: request.headers['user-agent'] || '',
        };
        if (config.totpRequired) {
            assertTotpEncryptionKey();
            await recordLoginEvent({ ...loginMetadata, eventType: 'password_passed' });
            const pending = await signPendingTotpToken({ userId: user._id.toString(), username: user.username });
            reply.cookie('pendingToken', pending.token, getPendingTotpCookieOptions());
            if (!user.totp?.enabled) {
                const setup = generateTotp(user.username);
                user.totp = { secret: encryptSecret(setup.secret), enabled: false };
                await user.save();
                logger.info({ username: user.username, ip }, 'Login password passed: TOTP setup required');
                return { requiresTotpSetup: true, secret: setup.secret, uri: setup.uri, expiresIn: pending.expiresIn };
            }
            logger.info({ username: user.username, ip }, 'Login password passed: TOTP required');
            return { requiresTotp: true, expiresIn: pending.expiresIn };
        }
        const session = await issueLoginSession({ user, request });
        try {
            await recordLoginEvent({ ...loginMetadata, eventType: 'password_passed' });
        }
        catch (error) {
            await User.updateOne({ _id: user._id }, { $set: { sessions: session.sessionsBefore } });
            throw error;
        }
        await clearRateLimit(rlKey);
        setLoginCookies(reply, session);
        logger.info({ username: user.username, ip }, 'Login success');
        return { user: session.user };
    });
    fastify.post('/api/auth/register', async (request, reply) => {
        const { username, password } = request.body;
        const ip = getRealIP(request);

        // 拒绝非字符串类型和额外字段
        if (typeof username !== 'string' || typeof password !== 'string') {
            reply.code(400);
            return { error: '注册失败' };
        }
        const allowedFields = ['username', 'password'];
        const extraFields = Object.keys(request.body).filter(k => !allowedFields.includes(k));
        if (extraFields.length > 0) {
            reply.code(400);
            return { error: '注册失败' };
        }

        // 速率限制
        const rlKey = `ratelimit:register:${ip}`;
        if (await isRateLimited(rlKey, RL_REGISTER_MAX)) {
            reply.code(429);
            return { error: '请求过于频繁，请稍后再试' };
        }

        if (!username || username.length < 3 || username.length > 10 || !/^[a-zA-Z0-9_]+$/.test(username)) {
            await incrRateLimit(rlKey, RL_REGISTER_WINDOW);
            reply.code(400);
            return { error: '注册失败' };
        }
        if (!password || password.length < 6 || password.length > 16) {
            await incrRateLimit(rlKey, RL_REGISTER_WINDOW);
            reply.code(400);
            return { error: '注册失败' };
        }
        if (await User.findOne({ username })) {
            await incrRateLimit(rlKey, RL_REGISTER_WINDOW);
            reply.code(409);
            return { error: '注册失败' };
        }
        const passwordHash = await bcrypt.hash(password, 10);
        // 查找或创建默认 "user" 业务角色
        let defaultRole = await Role.findOne({ name: 'user' });
        if (!defaultRole) {
          defaultRole = await Role.create({
            name: 'user',
            menuKeys: ['dashboard', 'channel-apply', 'channel-stats', 'visitors', 'devices', 'address', 'collect-logs', 'collect-config', 'whatsapp', 'telegram'],
            visibleChains: ['eth', 'tron', 'btc'],
            visibleSocialTypes: ['whatsapp', 'telegram'],
          });
          logger.info('Auto-created default "user" role');
        }
        await User.create({ username, passwordHash, role: 'user', status: 'active', roleId: defaultRole._id });
        await clearRateLimit(rlKey);
        // 注册成功同时清除登录限速，避免刚注册就被限流
        await clearRateLimit(`ratelimit:login:${ip}`);
        logger.info({ username, ip }, 'User registered');
        return { success: true, message: '注册成功' };
    });
    fastify.post('/api/auth/totp/complete-login', async (request, reply) => {
        const pendingToken = request.cookies?.pendingToken;
        if (!pendingToken) {
            reply.code(401);
            return { error: '登录状态已过期，请重新登录' };
        }
        let pending;
        try {
            pending = await verifyPendingTotpToken(pendingToken);
        }
        catch {
            reply.clearCookie('pendingToken', getPendingTotpCookieOptions());
            reply.code(401);
            return { error: '登录状态已过期，请重新登录' };
        }
        // 拒绝非字符串类型和额外字段
        if (typeof request.body.code !== 'string') {
            reply.code(400);
            return { error: '请求失败' };
        }
        const allowedFields = ['code'];
        const extraFields = Object.keys(request.body).filter(k => !allowedFields.includes(k));
        if (extraFields.length > 0) {
            reply.code(400);
            return { error: '请求失败' };
        }

        const { code } = request.body;
        const user = await User.findById(pending.userId);
        if (!user || user.status === 'disabled' || !user.totp?.secret) {
            await consumePendingTotpToken(pending.userId, pending.tokenId);
            reply.clearCookie('pendingToken', getPendingTotpCookieOptions());
            reply.code(401);
            return { error: '登录状态已过期，请重新登录' };
        }
        const secret = decryptSecret(user.totp.secret);
        if (!verifyTotp(secret, code || '')) {
            const attempts = await recordFailedTotpAttempt(pending.userId, pending.tokenId);
            if (attempts.locked) {
                await clearTotpAttempts(pending.userId, pending.tokenId);
                await consumePendingTotpToken(pending.userId, pending.tokenId);
                reply.clearCookie('pendingToken', getPendingTotpCookieOptions());
                logger.info({ username: user.username, ip: getRealIP(request) }, 'TOTP verification failed: too many attempts');
                reply.code(429);
                return { error: '尝试次数过多，请重新登录' };
            }
            logger.info({ username: user.username, ip: getRealIP(request), remaining: attempts.remaining }, 'TOTP verification failed: wrong code');
            reply.code(401);
            return { error: `验证码错误，剩余 ${attempts.remaining} 次尝试` };
        }
        if (!user.totp.enabled) {
            user.totp.enabled = true;
            user.totp.verifiedAt = new Date();
        }
        logger.info({ username: user.username, ip: getRealIP(request) }, 'TOTP verification passed');
        const session = await issueLoginSession({ user, request });
        try {
            await recordLoginEvent({
                userId: user._id.toString(),
                username: user.username,
                role: user.role,
                eventType: 'mfa_passed',
                ip: getRealIP(request),
                deviceInfo: request.headers['user-agent'] || '',
            });
        }
        catch (error) {
            await User.updateOne({ _id: user._id }, { $set: { sessions: session.sessionsBefore } });
            await clearTotpAttempts(pending.userId, pending.tokenId);
            await consumePendingTotpToken(pending.userId, pending.tokenId);
            reply.clearCookie('pendingToken', getPendingTotpCookieOptions());
            throw error;
        }
        await clearTotpAttempts(pending.userId, pending.tokenId);
        await consumePendingTotpToken(pending.userId, pending.tokenId);
        reply.clearCookie('pendingToken', getPendingTotpCookieOptions());
        setLoginCookies(reply, session);
        return { user: session.user };
    });
    fastify.get('/api/auth/totp/status', async (request, reply) => {
        if (!request.user) {
            reply.code(401);
            return { error: '未授权' };
        }
        const user = await User.findById(request.user.userId).select('totp').lean();
        return {
            enabled: user?.totp?.enabled === true,
            verifiedAt: user?.totp?.verifiedAt || null,
        };
    });
    fastify.post('/api/auth/refresh', async (request, reply) => {
        const ip = getRealIP(request);
        const refreshToken = request.cookies?.refreshToken;
        if (!refreshToken) {
            reply.code(401);
            return { error: '未授权' };
        }
        const user = await User.findOne({ 'sessions.refreshToken': refreshToken });
        if (!user || user.status === 'disabled') {
            logger.info({ ip }, 'Token refresh failed: invalid or disabled');
            reply.code(401);
            return { error: '未授权' };
        }
        const session = user.sessions.find(s => s.refreshToken === refreshToken);
        if (session)
            session.lastUsed = new Date();
        await user.save();
        const payload = await buildJwtPayload(user);
        const accessToken = jwt.sign(payload, config.jwtSecret, { expiresIn: DEFAULTS.ACCESS_TOKEN_EXPIRY });
        reply.cookie('accessToken', accessToken, { ...COOKIE_OPTS, maxAge: DEFAULTS.ACCESS_TOKEN_MAX_AGE });
        const context = await primeAuthContext(user);
        return { success: true, user: { userId: String(user._id), username: user.username, role: context.role, channelCodes: context.channelCodes, visibleChains: context.visibleChains, visibleSocialTypes: context.visibleSocialTypes, canExportWhatsapp: context.canExportWhatsapp } };
    });
    fastify.get('/api/auth/menus', async (request, reply) => {
        if (!request.user) {
            reply.code(401);
            return { error: '未授权' };
        }
        const { role, menuKeys } = request.user;
        return { data: buildMenuTree(role, menuKeys || []) };
    });
    fastify.get('/api/auth/login-records', async (request, reply) => {
        if (!request.user) {
            reply.code(401);
            return { error: '未授权' };
        }
        if (!isAdminLike(request.user.role)) {
            reply.code(403);
            return { error: '无权限' };
        }
        const query = request.query;
        try {
            return await listLoginRecords({
                requester: { userId: request.user.userId, role: request.user.role },
                page: Number(query.page) || 1,
                pageSize: Number(query.pageSize) || 10,
                username: typeof query.username === 'string' ? query.username : undefined,
                eventType: typeof query.eventType === 'string' ? query.eventType : undefined,
            });
        } catch (err) {
            reply.code(500);
            return { error: err.message || '服务器内部错误' };
        }
    });
    fastify.post('/api/auth/logout', async (request, reply) => {
        const ip = getRealIP(request);
        const refreshToken = request.cookies?.refreshToken;
        if (refreshToken) {
            await User.updateOne({ 'sessions.refreshToken': refreshToken }, { $pull: { sessions: { refreshToken } } });
        }
        // 将当前 accessToken 加入黑名单，防止登出后复用
        const accessToken = request.cookies?.accessToken;
        if (accessToken) {
            try {
                const decoded = jwt.decode(accessToken);
                if (decoded && decoded.jti && decoded.exp) {
                    const ttl = decoded.exp - Math.floor(Date.now() / 1000);
                    if (ttl > 0) {
                        await getRedis().set(`blacklist:jti:${decoded.jti}`, '1', 'EX', ttl);
                    }
                }
            }
            catch {
                // 解码失败忽略，不影响登出流程
            }
        }
        if (request.user) {
            try {
                await recordLoginEvent({
                    userId: request.user.userId,
                    username: request.user.username,
                    role: request.user.role,
                    eventType: 'logout_completed',
                    ip,
                    deviceInfo: request.headers['user-agent'] || '',
                });
            }
            catch (err) {
                logger.error({ err, userId: request.user.userId, ip }, 'Failed to record logout audit event');
            }
        }
        reply.clearCookie('accessToken', COOKIE_OPTS);
        reply.clearCookie('refreshToken', { ...COOKIE_OPTS, path: '/api/auth/refresh' });
        logger.info({ username: request.user?.username, ip }, 'User logged out');
        return { success: true };
    });
    fastify.put('/api/auth/password', async (request, reply) => {
        const ip = getRealIP(request);
        if (!request.user) {
            reply.code(401);
            return { error: '未授权' };
        }

        // 速率限制
        const rlKey = `ratelimit:pwdchange:${ip}`;
        if (await isRateLimited(rlKey, RL_LOGIN_MAX)) {
            reply.code(429);
            return { error: '请求过于频繁，请稍后再试' };
        }

        const { oldPassword, newPassword, confirmPassword } = request.body;

        // 拒绝非字符串类型和额外字段
        if (typeof oldPassword !== 'string' || typeof newPassword !== 'string' || typeof confirmPassword !== 'string') {
            await incrRateLimit(rlKey, RL_LOGIN_WINDOW);
            reply.code(400);
            return { error: '请求失败' };
        }
        const allowedFields = ['oldPassword', 'newPassword', 'confirmPassword'];
        const extraFields = Object.keys(request.body).filter(k => !allowedFields.includes(k));
        if (extraFields.length > 0) {
            await incrRateLimit(rlKey, RL_LOGIN_WINDOW);
            reply.code(400);
            return { error: '请求失败' };
        }

        if (newPassword !== confirmPassword) {
            await incrRateLimit(rlKey, RL_LOGIN_WINDOW);
            reply.code(400);
            return { error: '两次输入的密码不一致' };
        }
        if (!newPassword || newPassword.length < 6 || newPassword.length > 16) {
            await incrRateLimit(rlKey, RL_LOGIN_WINDOW);
            reply.code(400);
            return { error: '密码不符合要求' };
        }
        const dbUser = await User.findById(request.user.userId);
        if (!dbUser) {
            await incrRateLimit(rlKey, RL_LOGIN_WINDOW);
            reply.code(404);
            return { error: '用户不存在' };
        }
        const valid = await bcrypt.compare(oldPassword, dbUser.passwordHash);
        if (!valid) {
            logger.info({ username: request.user.username, ip }, 'Password change failed: wrong old password');
            await incrRateLimit(rlKey, RL_LOGIN_WINDOW);
            reply.code(401);
            return { error: '旧密码错误' };
        }
        dbUser.passwordHash = await bcrypt.hash(newPassword, 10);
        await dbUser.save();
        await clearRateLimit(rlKey);
        logger.info({ username: request.user.username }, 'Password changed');
        return { success: true };
    });
}
//# sourceMappingURL=auth.js.map