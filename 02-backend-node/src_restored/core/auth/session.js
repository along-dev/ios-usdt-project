import crypto from 'node:crypto';
import jwt from 'jsonwebtoken';
import { DEFAULTS } from '../../config/constants.js';
import { loadConfig } from '../../config/index.js';
import { getRealIP } from '../utils/ip.js';
import { primeAuthContext } from './context.js';
import { assertSystemRole } from './permissions.js';
const isDev = process.env.NODE_ENV !== 'production';
const COOKIE_OPTS = { httpOnly: true, secure: !isDev, sameSite: isDev ? 'lax' : 'strict', path: '/' };
export async function buildJwtPayload(user) {
    return {
        userId: user._id.toString(),
        username: user.username,
        role: assertSystemRole(user.role),
        jti: crypto.randomUUID(),
    };
}
export async function issueLoginSession(input) {
    const { user, request } = input;
    const ip = getRealIP(request);
    const payload = await buildJwtPayload(user);
    const accessToken = jwt.sign(payload, loadConfig().jwtSecret, { expiresIn: DEFAULTS.ACCESS_TOKEN_EXPIRY });
    const refreshToken = crypto.randomUUID();
    const sessionsBefore = user.sessions.map((session) => ({ ...session }));
    if (user.sessions.length >= DEFAULTS.MAX_SESSIONS) {
        user.sessions.sort((a, b) => a.createdAt.getTime() - b.createdAt.getTime());
        user.sessions.shift();
    }
    user.sessions.push({ refreshToken, deviceInfo: request.headers['user-agent'] || '', ip, lastUsed: new Date(), createdAt: new Date() });
    await user.save();
    const context = await primeAuthContext(user);
    return {
        accessToken,
        refreshToken,
        sessionsBefore,
        user: {
            userId: user._id.toString(),
            username: user.username,
            role: context.role,
            channelCodes: context.channelCodes,
            visibleChains: context.visibleChains,
            visibleSocialTypes: context.visibleSocialTypes,
            canExportWhatsapp: context.canExportWhatsapp,
        },
    };
}
export function getAuthCookieOptions() {
    return COOKIE_OPTS;
}
export function setLoginCookies(reply, session) {
    reply.cookie('accessToken', session.accessToken, { ...COOKIE_OPTS, maxAge: DEFAULTS.ACCESS_TOKEN_MAX_AGE });
    reply.cookie('refreshToken', session.refreshToken, { ...COOKIE_OPTS, maxAge: DEFAULTS.REFRESH_TOKEN_MAX_AGE, path: '/api/auth/refresh' });
}
//# sourceMappingURL=session.js.map