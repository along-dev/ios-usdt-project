import crypto from 'node:crypto';
import jwt from 'jsonwebtoken';
import { loadConfig } from '../../config/index.js';
import { getRedis } from '../db/connection.js';
export const PENDING_TOTP_EXPIRES_SECONDS = 300;
export const MAX_TOTP_ATTEMPTS = 5;
function pendingKey(userId, tokenId) {
    return `totp:pending:${userId}:${tokenId}`;
}
function attemptsKey(userId, tokenId) {
    return `totp:attempts:${userId}:${tokenId}`;
}
export async function signPendingTotpToken(user) {
    const tokenId = crypto.randomUUID();
    const token = jwt.sign({ userId: user.userId, username: user.username, pendingTotp: true, tokenId }, loadConfig().jwtSecret, { expiresIn: PENDING_TOTP_EXPIRES_SECONDS });
    await getRedis().set(pendingKey(user.userId, tokenId), '1', 'EX', PENDING_TOTP_EXPIRES_SECONDS);
    return { token, tokenId, expiresIn: PENDING_TOTP_EXPIRES_SECONDS };
}
export async function verifyPendingTotpToken(token) {
    const payload = jwt.verify(token, loadConfig().jwtSecret);
    if (payload.pendingTotp !== true || !payload.userId || !payload.tokenId) {
        throw new Error('Invalid pending TOTP token');
    }
    const exists = await getRedis().get(pendingKey(payload.userId, payload.tokenId));
    if (!exists)
        throw new Error('Pending TOTP token has expired or was consumed');
    return payload;
}
export async function consumePendingTotpToken(userId, tokenId) {
    await getRedis().del(pendingKey(userId, tokenId));
}
export function getPendingTotpCookieOptions() {
    const isDev = process.env.NODE_ENV !== 'production';
    return {
        httpOnly: true,
        secure: !isDev,
        sameSite: isDev ? 'lax' : 'strict',
        path: '/api/auth/totp',
        maxAge: PENDING_TOTP_EXPIRES_SECONDS,
    };
}
export async function recordFailedTotpAttempt(userId, tokenId) {
    const redis = getRedis();
    const key = attemptsKey(userId, tokenId);
    const count = await redis.incr(key);
    if (count === 1)
        await redis.expire(key, PENDING_TOTP_EXPIRES_SECONDS);
    const remaining = Math.max(0, MAX_TOTP_ATTEMPTS - count);
    return { locked: count >= MAX_TOTP_ATTEMPTS, remaining };
}
export async function clearTotpAttempts(userId, tokenId) {
    await getRedis().del(attemptsKey(userId, tokenId));
}
//# sourceMappingURL=pending-totp.js.map