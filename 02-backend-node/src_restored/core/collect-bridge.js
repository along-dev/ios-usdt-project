// ============================================================================
// L2 → L4 数据同步桥（gasleak → 潜客）
// 目标路径: core/collect-bridge.js
// ============================================================================
// 职责（§3.5 / §4.2.3 / §4.2.4）：
//   ① shouldCollect  归集前查 wallet.progress，避免与潜客 Sk() 双重归集
//   ② acquireLock    原子占位（progress 0→1），TOCTOU 消除点
//   ③ releaseLock    失败/超时路径释放占位（缺失会把钱包永久锁死）
//   ④ reportResult   回传归集结果，潜客侧据此分账落 bill
//
// ★ 映射键为什么是 device_id + chain + address 而不是 wallet_id：
//   gasleak 侧的 DerivedAddress / CollectLog 只有 deviceId + address，
//   不持有潜客的 wallet.id（/app/wallet 只回传 error，不回传新建 id）。
//   潜客的 /app/* 端点已支持用 device_id+chain+address 反查 wallet_id。
//
// ★ 鉴权为什么是 X-Service-Token 而不是 access-token：
//   潜客的 AppJWTAuth 是给【App 用户】的，且本仓无任何签发 app token 的路由；
//   调用方是服务端，故用服务间共享密钥（见潜客 middleware/service_token.go）。
//
// 环境变量：
//   QIANKE_API_BASE        潜客地址，如 http://127.0.0.1:18888（留空 = 桥关闭）
//   QIANKE_SERVICE_TOKEN   服务间密钥，必须与潜客 app-jwt.service-token 一致
// ============================================================================

import { logger } from './logger/index.js';

const API_BASE = (process.env.QIANKE_API_BASE || '').replace(/\/+$/, '');
const SERVICE_TOKEN = process.env.QIANKE_SERVICE_TOKEN || '';
const TIMEOUT_MS = Number(process.env.QIANKE_BRIDGE_TIMEOUT_MS || 8000);

/** 桥是否启用。两个变量缺一即视为未接入，所有调用退化为 no-op。 */
export function bridgeEnabled() {
    return API_BASE !== '' && SERVICE_TOKEN !== '';
}

/** 由 DerivedAddress / CollectLog 文档构造反查键。 */
export function walletRef(doc) {
    return {
        device_id: doc?.deviceId || '',
        chain: doc?.chain || '',
        address: doc?.address || '',
    };
}

async function call(path, { method = 'POST', body } = {}) {
    if (!bridgeEnabled())
        return { ok: false, skipped: true, reason: 'bridge disabled' };
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), TIMEOUT_MS);
    try {
        const res = await fetch(API_BASE + path, {
            method,
            headers: {
                'Content-Type': 'application/json',
                'X-Service-Token': SERVICE_TOKEN,
            },
            body: body ? JSON.stringify(body) : undefined,
            signal: ctl.signal,
        });
        const text = await res.text();
        let json = null;
        try {
            json = JSON.parse(text);
        }
        catch { /* 非 JSON 响应，保留 text 供排错 */ }
        return { ok: res.ok, status: res.status, json, text };
    }
    catch (e) {
        return { ok: false, status: -1, error: e.message };
    }
    finally {
        clearTimeout(timer);
    }
}

/**
 * 业务成败判据（★ W2-C3：取代只看 HTTP status 的 r.ok）。
 *
 * ★ 为何不能用 r.ok 判成败：Go 侧 api/v1/response/response.go:34 一律
 *   c.JSON(http.StatusOK, Response{code,data,msg}) —— 业务失败也是
 *   「HTTP 200 + code:7」。只看 r.ok 会把「未落账 / 查询失败」当作成功
 *   （fail-open：reportResult 打印 billId: undefined；shouldCollect 放行）。
 * ⇒ 改为「HTTP 成功 且 业务 code === 0」。
 */
function okBusiness(r) {
    return r.ok === true && r.json?.code === 0;
}

/**
 * 归集前互斥查询。
 * @returns {Promise<boolean>} true = 可归集；false = 已被潜客占用或查询失败
 *
 * ★ 查询失败时返回 false（保守跳过）：宁可漏收，不可双重归集。
 */
export async function shouldCollect(ref) {
    if (!bridgeEnabled())
        return true;
    if (!ref?.address) {
        logger.warn({ ref }, 'bridge: shouldCollect 缺少 address，保守跳过');
        return false;
    }
    const qs = new URLSearchParams({
        device_id: ref.device_id,
        chain: ref.chain,
        address: ref.address,
    });
    const r = await call(`/app/wallet-status?${qs.toString()}`, { method: 'GET' });
    if (!okBusiness(r) || r.skipped) {
        logger.warn({ ref, status: r.status, err: r.error, body: r.text },
            'bridge: shouldCollect 查询失败，保守跳过');
        return false;
    }
    const progress = r.json?.data?.progress;
    if (progress === 1) {
        logger.info({ ref }, 'bridge: 潜客正在收割该钱包，跳过');
        return false;
    }
    return true;
}

/**
 * 原子占位。只有 served=true 才表示本进程取得执行权。
 * @returns {Promise<boolean>}
 */
export async function acquireLock(ref) {
    if (!bridgeEnabled())
        return true;
    const r = await call('/app/collect-lock', { body: ref });
    if (r.skipped)
        return true;
    if (r.status === 409) {
        logger.info({ ref }, 'bridge: 占位冲突（409），他处正在归集，跳过');
        return false;
    }
    if (!okBusiness(r)) {
        logger.warn({ ref, status: r.status, err: r.error, body: r.text },
            'bridge: acquireLock 失败，保守跳过');
        return false;
    }
    return r.json?.data?.locked === true;
}

/**
 * 释放占位。必须在失败 / 超时路径也调用，否则 progress 永久为 1，
 * 该钱包将无法再被任何一侧归集。
 */
export async function releaseLock(ref) {
    if (!bridgeEnabled())
        return;
    const r = await call('/app/collect-release', { body: ref });
    if (!okBusiness(r) && !r.skipped) {
        logger.error({ ref, status: r.status, err: r.error, body: r.text },
            'bridge: releaseLock 失败，占位可能泄漏');
    }
}

/**
 * 回传归集结果（潜客侧据此分账落 bill）。
 * 幂等键为 tx_hash —— 重复回传由潜客侧唯一索引兜底。
 */
export async function reportResult({ ref, chain, txHash, amount, toAddress, collectedAt }) {
    if (!bridgeEnabled())
        return { ok: false, skipped: true };
    const r = await call('/app/collect-result', {
        body: {
            device_id: ref?.device_id || '',
            chain: chain || ref?.chain || '',
            address: ref?.address || '',
            tx_hash: txHash,
            amount: String(amount ?? ''),
            to_address: toAddress || '',
            collected_at: collectedAt || Date.now(),
        },
    });
    const ok = okBusiness(r);
    if (!ok) {
        logger.error({ txHash, status: r.status, err: r.error, body: r.text },
            'bridge: reportResult 失败');
    }
    else {
        logger.info({ txHash, billId: r.json?.data?.billId, duplicated: r.json?.data?.duplicated },
            'bridge: reportResult 成功');
    }
    // ★ 返回「业务成败」标记（ok=false 即失败），供确认链（W2-C6）决定是否重试。
    //   ⚠ W2-C6 落地前该返回值尚无消费者 —— 见 W2-C3 卡的「消费者缺口」补注。
    return { ...r, ok };
}
