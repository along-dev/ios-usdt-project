import { TatumKey } from '../db/models/index.js';
import { TATUM_ENDPOINTS } from './constants.js';
import { logger } from '../logger/index.js';
// ─── Rate Limiter ──────────────────────────────────────────────────────────────
export class RateLimiter {
    maxTokens;
    refillRate;
    tokens;
    lastRefill;
    constructor(rps) {
        this.maxTokens = rps;
        this.refillRate = rps;
        this.tokens = rps;
        this.lastRefill = Date.now();
    }
    refill() {
        const now = Date.now();
        const added = ((now - this.lastRefill) / 1000) * this.refillRate;
        this.tokens = Math.min(this.maxTokens, this.tokens + added);
        this.lastRefill = now;
    }
    async acquire() {
        while (true) {
            this.refill();
            if (this.tokens >= 1) {
                this.tokens -= 1;
                return;
            }
            await sleep(1000 / this.refillRate);
        }
    }
}
// ─── Helpers ───────────────────────────────────────────────────────────────────
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
// ─── TatumClient ───────────────────────────────────────────────────────────────
export class TatumClient {
    rateLimiters = new Map();
    keyIndex = 0;
    cachedKeys = [];
    keysLoadedAt = 0;
    getRateLimiter(key) {
        let rl = this.rateLimiters.get(key);
        if (!rl) {
            rl = new RateLimiter(200);
            this.rateLimiters.set(key, rl);
        }
        return rl;
    }
    async pickKey() {
        if (Date.now() - this.keysLoadedAt > 10000) {
            this.cachedKeys = await TatumKey.find({ enabled: true }).lean();
            this.keysLoadedAt = Date.now();
        }
        if (this.cachedKeys.length === 0) {
            throw new Error('No enabled Tatum API keys available');
        }
        const key = this.cachedKeys[this.keyIndex % this.cachedKeys.length];
        this.keyIndex = (this.keyIndex + 1) % this.cachedKeys.length;
        return key;
    }
    async handleResponse(res, key, chain, method) {
        const text = await res.text();
        const data = text ? JSON.parse(text) : null;
        logger.info({ chain, method, status: res.status, data }, 'tatum response');
        if (res.status === 401 || res.status === 403) {
            const errCode = data?.errorCode || '';
            const errMsg = data?.message || '';
            logger.error({ chain, method, keyName: key.name, status: res.status, errCode }, 'tatum auth error');
            throw new Error(`Tatum ${res.status} [${errCode}]: ${errMsg}`);
        }
        if (res.status === 429) {
            logger.warn({ chain, method, keyName: key.name }, 'tatum rate limit hit, retrying once');
            await sleep(1000);
            throw new Error('Tatum rate limit exceeded after retry');
        }
        if (res.status >= 400) {
            const msg = data?.message || `HTTP ${res.status}`;
            throw new Error(`Tatum error ${res.status}: ${msg}`);
        }
        return data;
    }
    async ethRpc(method, params) {
        const key = await this.pickKey();
        const rl = this.getRateLimiter(key.apiKey);
        await rl.acquire();
        const body = {
            jsonrpc: '2.0',
            id: 1,
            method,
            params,
        };
        logger.info({ chain: 'eth', method, keyName: key.name, body }, 'tatum request');
        const res = await fetch(TATUM_ENDPOINTS.eth, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': key.apiKey,
            },
            body: JSON.stringify(body),
            signal: AbortSignal.timeout(10000),
        });
        return this.handleResponse(res, key, 'eth', method);
    }
    async tronApi(path, body) {
        const key = await this.pickKey();
        const rl = this.getRateLimiter(key.apiKey);
        await rl.acquire();
        logger.info({ chain: 'tron', path, keyName: key.name, body }, 'tatum request');
        const res = await fetch(`${TATUM_ENDPOINTS.tron}${path}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': key.apiKey,
            },
            body: JSON.stringify(body),
            signal: AbortSignal.timeout(10000),
        });
        return this.handleResponse(res, key, 'tron', path);
    }
    async btcBalance(address) {
        const key = await this.pickKey();
        const rl = this.getRateLimiter(key.apiKey);
        await rl.acquire();
        const url = `${TATUM_ENDPOINTS.btcDataApi}balance?chain=bitcoin-mainnet&address=${encodeURIComponent(address)}`;
        logger.info({ chain: 'btc', method: 'btcBalance', keyName: key.name, url, address }, 'tatum request');
        const res = await fetch(url, {
            method: 'GET',
            headers: {
                'x-api-key': key.apiKey,
            },
            signal: AbortSignal.timeout(10000),
        });
        return this.handleResponse(res, key, 'btc', 'btcBalance');
    }
    async createSubscription(address, chain, webhookUrl) {
        const key = await this.pickKey();
        const rl = this.getRateLimiter(key.apiKey);
        await rl.acquire();
        const requestBody = {
            type: 'ADDRESS_EVENT',
            attr: {
                address,
                chain,
                url: webhookUrl,
            },
        };
        logger.info({ chain, method: 'createSubscription', keyName: key.name, requestBody }, 'tatum request');
        const res = await fetch(TATUM_ENDPOINTS.subscription, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': key.apiKey,
            },
            body: JSON.stringify(requestBody),
            signal: AbortSignal.timeout(10000),
        });
        const data = (await this.handleResponse(res, key, chain, 'createSubscription'));
        if (!data.id) {
            throw new Error(`Tatum createSubscription returned empty id, response: ${JSON.stringify(data)}`);
        }
        return {
            subscriptionId: data.id,
            keyId: key._id,
        };
    }
    async cancelSubscription(subscriptionId, keyId) {
        const key = await TatumKey.findById(keyId);
        if (!key) {
            throw new Error(`TatumKey not found: ${keyId}`);
        }
        const rl = this.getRateLimiter(key.apiKey);
        await rl.acquire();
        const url = `${TATUM_ENDPOINTS.subscription}/${subscriptionId}`;
        logger.info({ chain: 'subscription', method: 'cancelSubscription', keyName: key.name, url, subscriptionId }, 'tatum request');
        const res = await fetch(url, {
            method: 'DELETE',
            headers: {
                'x-api-key': key.apiKey,
            },
            signal: AbortSignal.timeout(10000),
        });
        await this.handleResponse(res, key, 'subscription', 'cancelSubscription');
    }
}
export const tatumClient = new TatumClient();
//# sourceMappingURL=client.js.map