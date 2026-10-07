import { logger } from '../logger/index.js';
import https from 'node:https';
import http from 'node:http';
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
function isRetryableStatus(status) {
    return status === 429 || status === 503;
}
function isTimeoutError(err) {
    return err?.name === 'AbortError' || err?.name === 'TimeoutError';
}
const DEFAULT_OPTIONS = {
    maxRetries: 1,
    delayMs: 3000,
    timeoutMs: 10_000,
};
/**
 * Native HTTPS request wrapper that forces IPv4.
 * Avoids undici's Happy Eyeballs bug where unreachable IPv6 causes ETIMEDOUT.
 */
function nativeFetch(url, init) {
    return new Promise((resolve, reject) => {
        const u = new URL(url);
        const mod = u.protocol === 'https:' ? https : http;
        const options = {
            hostname: u.hostname,
            port: u.port || (u.protocol === 'https:' ? 443 : 80),
            path: u.pathname + u.search,
            method: init.method || 'GET',
            headers: init.headers || {},
            family: 4,
            signal: init.signal,
        };
        const req = mod.request(options, (res) => {
            const chunks = [];
            res.on('data', chunk => chunks.push(chunk));
            res.on('end', () => {
                const body = Buffer.concat(chunks);
                resolve({
                    ok: res.statusCode >= 200 && res.statusCode < 300,
                    status: res.statusCode,
                    json: async () => JSON.parse(body.toString()),
                    text: async () => body.toString(),
                });
            });
            res.on('error', reject);
        });
        req.on('error', reject);
        if (init.body) req.write(init.body);
        req.end();
    });
}
/**
 * fetch 封装：自动重试 429/503/超时，带详细日志。
 * 返回 Response 对象，调用方自行判断 resp.ok 和解析 body。
 * 404 视为正常响应（不重试），由调用方决定如何处理。
 */
export async function fetchWithRetry(url, init, opts) {
    const { maxRetries, delayMs, label, timeoutMs } = { ...DEFAULT_OPTIONS, ...opts };
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
            const resp = await nativeFetch(url, {
                ...init,
                signal: AbortSignal.timeout(timeoutMs),
            });
            // 成功或 404（预期的"未找到"）直接返回
            if (resp.ok || resp.status === 404)
                return resp;
            // 可重试的状态码
            if (isRetryableStatus(resp.status) && attempt < maxRetries) {
                const text = await resp.text().catch(() => '');
                logger.warn({ label, status: resp.status, attempt: attempt + 1, maxRetries, response: text }, 'rpc: rate limited, retrying');
                await sleep(delayMs);
                continue;
            }
            // 不可重试或已达最大重试次数，返回原始响应
            return resp;
        }
        catch (err) {
            // 超时可重试
            if (isTimeoutError(err) && attempt < maxRetries) {
                logger.warn({ label, error: err.message, attempt: attempt + 1, maxRetries }, 'rpc: timeout, retrying');
                await sleep(delayMs);
                continue;
            }
            // 不可重试的网络错误
            throw err;
        }
    }
    // 不应到达这里（for 循环最后一次迭代会 return 或 throw）
    throw new Error(`fetchWithRetry: unexpected end of retries for ${label}`);
}
/**
 * 用于 ethers provider.send 拦截的重试包装。
 * 检测 Infura 限流特征（JSON-RPC error code -32005, 或消息含 rate/429/too many）。
 */
export function isEthRateLimitError(err) {
    if (err?.code === -32005)
        return true;
    const msg = (err?.message || '').toLowerCase();
    return msg.includes('rate') || msg.includes('429') || msg.includes('too many');
}
export async function withRetry(fn, opts) {
    const { maxRetries, delayMs, label, isRetryable } = opts;
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
            return await fn();
        }
        catch (err) {
            if (isRetryable(err) && attempt < maxRetries) {
                logger.warn({ label, error: err.message, attempt: attempt + 1, maxRetries }, 'rpc: retryable error, retrying');
                await sleep(delayMs);
                continue;
            }
            throw err;
        }
    }
    throw new Error(`withRetry: unexpected end of retries for ${label}`);
}
//# sourceMappingURL=rpc-retry.js.map