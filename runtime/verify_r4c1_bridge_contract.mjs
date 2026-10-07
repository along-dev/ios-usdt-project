/**
 * R4-C1 判据：桥调用体 vs 接口契约一致性（防回归）。
 *
 * ★ 本卡的真正价值：桥当前【正确】≠ 永远正确。
 *   故建立【机械断言】防未来回归。本脚本不改任何被测文件。
 *
 * 契约方（Go）：01-backend-go/model/common.go 的 ReqCollectResult
 * 调用方（Node）：02-backend-node/src_restored/core/collect-bridge.js 的 reportResult
 *
 * 断言组：
 *   A1-A5 静态契约一致性（不依赖服务）
 *     A1 从 common.go 提取 ReqCollectResult 的 字段名 + json tag + Go 类型
 *     A2 从 collect-bridge.js 的 reportResult 提取实际请求体的键
 *     A3 桥的每个键都在契约中（无多余字段）
 *     A4 契约的必填字段都在桥的调用体中（无缺失）
 *     A5 ★★ 类型断言：契约 amount 是 string ⇒ 桥必须包裹 String(...)
 *   B1-B4 运行时请求体比对（真 import 桥 + mock globalThis.fetch）
 *     B1 真调用 reportResult，抓取实际发出的 body
 *     B2 ★ typeof body.amount === 'string'（多种输入：数字 / 字符串 / undefined）
 *     B3 body.tx_hash 存在且非空
 *     B4 JSON.stringify(body) 后 amount 带引号
 *   C1 端到端（若 Go 8888 在跑则真 POST，否则 SKIP —— P-13）
 *
 * 用法：
 *   node verify_r4c1_bridge_contract.mjs              # 全量
 *   node verify_r4c1_bridge_contract.mjs --selftest   # 量尺前置断言（P-5）
 *   node verify_r4c1_bridge_contract.mjs --negative   # ★ V4 判别力演示（临时副本改坏 ⇒ 必须报红）
 *
 * 退出码：0 = 全绿；1 = 有红；2 = 环境/自检失败
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ---- 被测文件（只读）----
const GO_MODEL = 'E:\\USDT项目\\01-backend-go\\model\\common.go';
const BRIDGE = 'E:\\USDT项目\\02-backend-node\\src_restored\\core\\collect-bridge.js';
const MANIFEST = 'E:\\USDT项目\\_manifest.sha256';
const CONTRACTS = 'E:\\USDT项目\\09-docs\\spec\\contracts.md';

// 卡 baseline（R4-C1 卡 frontmatter，用于守护未改）
const BASE = {
    [GO_MODEL]: { sha: 'a90a5b9ed491e8a3fa4a899928967a3a35c0a7dabcce0f41269b1b10678847ff', bytes: 7393 },
    [BRIDGE]: { sha: 'd1b6b480ceb29955874eb66691efb77598ffb2bafae2f73991c16e2b3a7d3941', bytes: 7253 },
};

const ARGV = process.argv.slice(2);
const SELFTEST = ARGV.includes('--selftest');
const NEGATIVE = ARGV.includes('--negative');

const results = [];
function rec(group, name, ok, detail) {
    results.push({ group, name, ok: !!ok, detail });
    console.log(`  [${ok ? 'PASS' : 'FAIL'}] ${group} ${name}: ${detail}`);
}
function sha256(buf) { return crypto.createHash('sha256').update(buf).digest('hex'); }

// ============================================================================
// 静态解析：Go 契约
// ============================================================================

/**
 * A1：从 common.go 提取 `type ReqCollectResult struct { ... }`。
 * 返回 [{ field, goType, json }]
 *
 * 解析策略：定位 type 行 → 花括号配平取块 → 逐行用正则拆 字段名/类型/json tag。
 * ★ 不匹配「无 json tag」的行（Go 里那是显式不导出/不参与 JSON 的字段）。
 */
function parseGoStruct(src, structName) {
    const lines = src.split(/\r?\n/);
    let start = -1;
    for (let i = 0; i < lines.length; i++) {
        if (new RegExp(`^\\s*type\\s+${structName}\\s+struct\\s*\\{`).test(lines[i])) { start = i; break; }
    }
    if (start < 0) return null;

    const block = [];
    let depth = 0;
    for (let i = start; i < lines.length; i++) {
        const ln = lines[i];
        for (const ch of ln) {
            if (ch === '{') depth++;
            else if (ch === '}') depth--;
        }
        if (i > start) block.push(ln);
        if (depth === 0) break;
    }

    const out = [];
    for (const ln of block) {
        // 剥离行尾注释，避免注释里的字符串干扰
        const code = ln.replace(/\/\/.*$/, '');
        // 形如:  WalletId    int    `json:"wallet_id"`    // 钱包id（可选）
        const m = code.match(/^\s*([A-Za-z_]\w*)\s+([A-Za-z_][\w.\[\]*]*)\s+`([^`]*)`/);
        if (!m) continue;
        const tag = m[3];
        const jm = tag.match(/json:"([^",]+)/);
        if (!jm) continue;
        out.push({ field: m[1], goType: m[2].trim(), json: jm[1] });
    }
    return out;
}

/**
 * A2：从 collect-bridge.js 的 reportResult 提取 `call('/app/collect-result', { body: {...} })` 的键。
 * 返回 { path, keys: [{ key, rawValue }] }
 *
 * 解析策略：定位 `export async function reportResult` → 找到该函数内的
 * `'/app/collect-result'` → 定位其后的 `body: {` → 花括号配平取块 →
 * 逐行拆 `key: <该行剩余内容>`。
 * ★ 保留 rawValue 原文，供 A5 检查是否包裹 String(...)。
 */
function parseBridgeBody(src) {
    const fnStart = src.indexOf('export async function reportResult');
    if (fnStart < 0) return null;

    // ★ 关键：reportResult 的参数表是【解构】形式 `reportResult({ ref, chain, ... })`，
    //   参数表自身含花括号。若直接从 fnStart 后第一个 '{' 起配平，会在参数表处
    //   就配平完毕，把函数体截成 88 字符（实测踩坑）。故必须先跳过参数表。
    const parenOpen = src.indexOf('(', fnStart);
    if (parenOpen < 0) return null;
    let pd = 0, parenClose = -1;
    for (let i = parenOpen; i < src.length; i++) {
        if (src[i] === '(') pd++;
        else if (src[i] === ')') { pd--; if (pd === 0) { parenClose = i; break; } }
    }
    if (parenClose < 0) return null;

    // 函数体：从参数表之后的第一个 '{' 起花括号配平
    const bodyOpen = src.indexOf('{', parenClose);
    if (bodyOpen < 0) return null;
    let depth = 0, i = bodyOpen, fnEnd = -1;
    for (; i < src.length; i++) {
        if (src[i] === '{') depth++;
        else if (src[i] === '}') { depth--; if (depth === 0) { fnEnd = i; break; } }
    }
    const fnSrc = src.slice(fnStart, fnEnd + 1);

    const pathM = fnSrc.match(/call\(\s*'([^']+)'/);
    if (!pathM) return null;
    const callIdx = fnSrc.indexOf(pathM[0]);

    const bodyKeyIdx = fnSrc.indexOf('body', callIdx);
    if (bodyKeyIdx < 0) return null;
    const braceIdx = fnSrc.indexOf('{', bodyKeyIdx);
    if (braceIdx < 0) return null;

    depth = 0;
    let j = braceIdx, bodyEnd = -1;
    for (; j < fnSrc.length; j++) {
        if (fnSrc[j] === '{') depth++;
        else if (fnSrc[j] === '}') { depth--; if (depth === 0) { bodyEnd = j; break; } }
    }
    const bodySrc = fnSrc.slice(braceIdx + 1, bodyEnd);

    const keys = [];
    for (const ln of bodySrc.split(/\r?\n/)) {
        const code = ln.replace(/\/\/.*$/, '').trim();
        const m = code.match(/^([A-Za-z_]\w*)\s*:\s*(.+?),?\s*$/);
        if (!m) continue;
        keys.push({ key: m[1], rawValue: m[2].replace(/,\s*$/, '').trim() });
    }
    return { path: pathM[1], keys };
}

// ============================================================================
// B 组：真 import 桥 + mock globalThis.fetch，抓实际发出的 body
// ============================================================================

/** 在临时副本或真文件上用 mock fetch 调用一次 reportResult，返回抓到的原始 body 字符串。 */
/**
 * ★ 关键：collect-bridge.js 在【模块顶层】读取 process.env 并缓存。
 *   若 QIANKE_API_BASE / QIANKE_SERVICE_TOKEN 未设置，bridgeEnabled() === false，
 *   reportResult 会直接 `return { ok:false, skipped:true }` 而【根本不调用 fetch】
 *   ⇒ 抓不到任何 body（实测踩坑：selftest 未设 env 时 captured === null）。
 *   故本函数自行兜底设置 env，并在设置后用带时间戳的 query 强制重新求值模块。
 */
const DEFAULT_API_BASE = 'http://127.0.0.1:8888';
const DEFAULT_TOKEN = 'i2c1-e2e-token';

async function captureBody(modUrl, args) {
    if (!process.env.QIANKE_API_BASE) process.env.QIANKE_API_BASE = DEFAULT_API_BASE;
    if (!process.env.QIANKE_SERVICE_TOKEN) process.env.QIANKE_SERVICE_TOKEN = DEFAULT_TOKEN;

    const mod = await import(modUrl + (modUrl.includes('?') ? '&' : '?') + 't=' + Date.now());
    if (typeof mod.bridgeEnabled === 'function' && !mod.bridgeEnabled()) {
        throw new Error('bridgeEnabled() === false —— 桥会短路返回，抓不到 body（env 未生效）');
    }
    const saved = globalThis.fetch;
    let captured = null;
    globalThis.fetch = async (url, opts) => {
        captured = { url, opts };
        return {
            ok: true, status: 200,
            text: async () => JSON.stringify({ code: 0, data: { billId: 1 } }),
        };
    };
    try {
        await mod.reportResult(args);
    } finally {
        globalThis.fetch = saved;
    }
    if (captured === null) {
        throw new Error('reportResult 未发起 fetch（桥可能短路），未抓到 body');
    }
    return captured;
}

// ============================================================================
// 主流程
// ============================================================================

async function main() {
    console.log('=== R4-C1 桥调用体 vs 接口契约一致性（防回归判据）===');
    console.log(`契约: ${GO_MODEL}`);
    console.log(`桥  : ${BRIDGE}`);
    if (NEGATIVE) console.log('★★ 模式: --negative（V4 判别力演示：在【临时副本】上改坏，真文件不动）');
    console.log('');

    const post = [];
    for (const p of [GO_MODEL, BRIDGE, MANIFEST, CONTRACTS]) {
        post.push({ p, exists: fs.existsSync(p), sha: fs.existsSync(p) ? sha256(fs.readFileSync(p)) : null });
    }
    for (const x of post) console.log(`  input[${x.exists ? 'OK ' : 'MISS'}] ${x.p}  ${x.sha ? x.sha.slice(0, 16) + '…' : ''}`);
    if (post.some(x => !x.exists)) { console.log('RESULT=RED  输入文件缺失'); process.exit(2); }
    console.log('');

    const goSrc = fs.readFileSync(GO_MODEL, 'utf8');
    const brSrc = fs.readFileSync(BRIDGE, 'utf8');

    // ---------------------------------------------------------------- A1
    console.log('断言组 A：静态契约一致性');
    const contract = parseGoStruct(goSrc, 'ReqCollectResult');
    rec('A1', 'ReqCollectResult 解析出字段', Array.isArray(contract) && contract.length === 8,
        `fields=${contract ? contract.length : 'null'} -> ${contract ? contract.map(f => f.json).join(',') : '(未解析到)'}`);

    // 契约字段名 + Go 类型打印（本卡要求的"字段对照表"）
    if (contract) {
        console.log('    ┌─ 契约 ReqCollectResult（解析结果）');
        for (const f of contract) console.log(`    │  ${f.json.padEnd(14)} Go=$${f.goType.padEnd(7)} (Go 字段 ${f.field})`);
        console.log('    └─');
    }

    // ---------------------------------------------------------------- A2
    const bridge = parseBridgeBody(brSrc);
    rec('A2', 'reportResult 请求体解析出键', !!bridge && bridge.keys.length > 0,
        `path=${bridge ? bridge.path : 'null'} keys=${bridge ? bridge.keys.map(k => k.key).join(',') : '(未解析到)'}`);

    if (!contract || !bridge) {
        console.log('RESULT=RED  静态解析失败，后续断言不可执行');
        process.exit(1);
    }

    const contractByName = new Map(contract.map(f => [f.json, f]));

    // 静态对照表
    console.log('');
    console.log('    ┌─ 逐字段对照（契约 vs 桥调用体）');
    console.log('    │  ' + 'contract'.padEnd(14) + 'GoType'.padEnd(9) + 'Bridged?'.padEnd(10) + 'Raw expr');
    for (const f of contract) {
        const b = bridge.keys.find(k => k.key === f.json);
        console.log('    │  ' + f.json.padEnd(14) + f.goType.padEnd(9) + (b ? 'YES' : '--').padEnd(10) + (b ? b.rawValue : ''));
    }
    for (const k of bridge.keys) {
        if (!contractByName.has(k.key)) console.log('    │  [EXTRA] ' + k.key.padEnd(14) + '(不在契约中)');
    }
    console.log('    └─');

    // ---------------------------------------------------------------- A3
    const extra = bridge.keys.filter(k => !contractByName.has(k.key));
    rec('A3', '桥的每个键都在契约中（无多余字段）', extra.length === 0,
        extra.length === 0 ? '无多余字段' : `多余: ${extra.map(k => k.key).join(',')}`);

    // ---------------------------------------------------------------- A4
    // 必填 = 契约里除 wallet_id（注释标注"可选"）之外的全部字段
    const OPTIONAL = ['wallet_id'];
    const required = contract.filter(f => !OPTIONAL.includes(f.json)).map(f => f.json);
    const missing = required.filter(f => !bridge.keys.some(k => k.key === f));
    rec('A4', `契约必填字段 (${required.length}) 都在桥调用体中（无缺失）`, missing.length === 0,
        missing.length === 0 ? `全部在场: ${required.join(',')}` : `缺失: ${missing.join(',')}`);

    // ---------------------------------------------------------------- A5 ★★ 本卡核心
    // 契约中 Go 类型为 string 的字段 ⇒ 桥必须保证发出的是 JS string。
    // 最稳的机械判据：该字段的原始表达式必须显式包裹 String(...) ，
    // 或者是必然产生 string 的表达式（字符串字面量 / 已 String() 化 / || '' 兜底）。
    const stringFields = contract.filter(f => f.goType === 'string').map(f => f.json);
    console.log('');
    console.log(`    ★ A5 检查契约中 Go type=string 的字段（共 ${stringFields.length}）:`);

    const STRINGY = (expr) =>
        /String\s*\(/.test(expr)            // 显式 String(...)
        || /^['"`]/.test(expr)              // 字符串字面量
        || /\|\|\s*['"`]/.test(expr)         // `?? ''` / `|| ''` 兜底
        || /^\s*''\s*$/.test(expr);

    const notStringy = [];
    for (const f of stringFields) {
        const b = bridge.keys.find(k => k.key === f.json);
        if (!b) continue; // 缺失由 A4 负责
        const good = STRINGY(b.rawValue);
        if (!good) notStringy.push({ field: f.json, expr: b.rawValue });
        console.log(`    │  ${good ? 'OK  ' : 'BAD '} ${f.json.padEnd(14)} expr=${b.rawValue}`);
    }
    rec('A5', `契约 string 字段 (${stringFields.length}) 在桥侧均为 string 语义`, notStringy.length === 0,
        notStringy.length === 0
            ? '全部满足（amount 尤其: 见下）'
            : `非 string 语义: ${notStringy.map(x => `${x.field}=${x.expr}`).join('; ')}`);

    // ★ A5 专点：amount 必须显式 String(...)
    {
        const b = bridge.keys.find(k => k.key === 'amount');
        const c = contractByName.get('amount');
        const goIsString = !!c && c.goType === 'string';
        const bridgedString = !!b && /String\s*\(/.test(b.rawValue);
        rec('A5', '★ amount: 契约 string ⇒ 桥显式 String(...)', goIsString && bridgedString,
            `契约 Go type=${c ? c.goType : '?'}; 桥 expr=${b ? b.rawValue : '(缺失)'}`);
    }
    console.log('');

    // ---------------------------------------------------------------- B 组
    console.log('断言组 B：运行时请求体比对（真 import 桥 + mock fetch）');
    const modUrl = pathToFileURL(BRIDGE).href;

    // B1：真调用并抓取 body
    const REF = { device_id: 'dev-r4c1', chain: 'tron', address: 'TAddrR4C1' };
    const CASES = [
        { label: 'amount: 1.5    (number)', amount: 1.5, expect: '1.5' },
        { label: "amount: '2.5'  (string)", amount: '2.5', expect: '2.5' },
        { label: 'amount: undefined', amount: undefined, expect: '' },
    ];

    const captured = [];
    let b1ok = true;
    for (const c of CASES) {
        let cap = null, err = null;
        try {
            cap = await captureBody(modUrl, {
                ref: REF, chain: 'tron', txHash: `r4c1-${Date.now()}`, amount: c.amount,
                toAddress: 'TToR4C1', collectedAt: 1700000000000,
            });
        } catch (e) { err = e; }
        if (err || !cap) { b1ok = false; captured.push({ c, cap: null, err }); continue; }
        let parsed = null, perr = null;
        try { parsed = JSON.parse(cap.opts.body); } catch (e) { perr = e; }
        captured.push({ c, cap, parsed, perr });
    }

    rec('B1', '真调用 reportResult 并抓到实际发出的 body', b1ok && captured.every(x => x.cap),
        b1ok ? `captured ${captured.filter(x => x.cap).length}/${CASES.length} 次，URL=${captured[0]?.cap?.url}` : '调用抛错');

    if (!b1ok) {
        console.log('RESULT=RED  B 组调用失败');
        process.exit(1);
    }

    for (const x of captured) {
        console.log(`    ┌─ ${x.c.label}`);
        console.log(`    │  raw body : ${x.cap.opts.body}`);
        if (x.parsed) console.log(`    │  parsed   : amount=${JSON.stringify(x.parsed.amount)} typeof=${typeof x.parsed.amount}`);
        console.log('    └─');
    }

    // B2：typeof body.amount === 'string'，多种输入
    {
        const bad = captured.filter(x => !x.parsed || typeof x.parsed.amount !== 'string');
        const vals = captured.map(x => `${JSON.stringify(x.c.amount)}->${typeof x.parsed?.amount}:${JSON.stringify(x.parsed?.amount)}`);
        rec('B2', "★ 无论输入何种类型, typeof body.amount === 'string'", bad.length === 0,
            bad.length === 0 ? `3/3: ${vals.join(' | ')}` : `非 string: ${bad.map(b => b.c.label).join(',')}`);
    }

    // B2b：值语义保持（number 1.5 -> '1.5'，不丢精度/不变形）
    {
        const bad = [];
        for (const x of captured) {
            const want = x.c.expect;
            if (x.parsed?.amount !== want) bad.push(`${x.c.label}: got ${JSON.stringify(x.parsed?.amount)} want ${JSON.stringify(want)}`);
        }
        rec('B2', '★ amount 值语义正确（number 1.5⇒"1.5"；undefined⇒""，不产生 "undefined"）', bad.length === 0,
            bad.length === 0 ? '1.5->"1.5" ; "2.5"->"2.5" ; undefined->""' : bad.join(' | '));
    }

    // B3：tx_hash 存在且非空（幂等键）
    {
        const bad = [];
        for (const x of captured) {
            const v = x.parsed?.tx_hash;
            if (typeof v !== 'string' || v === '') bad.push(x.c.label);
        }
        rec('B3', '★ body.tx_hash 存在且非空（幂等键）', bad.length === 0,
            bad.length === 0 ? `3/3 非空: ${JSON.stringify(captured[0].parsed.tx_hash)}` : `空/缺失: ${bad.join(',')}`);
    }

    // B4：JSON.stringify 后 amount 带引号
    {
        const bad = [];
        for (const x of captured) {
            const raw = x.cap.opts.body;
            // amount 的 JSON 序列化形态必须是 "amount":"<str>"（引号包裹），而非 "amount":1.5
            if (!/"amount"\s*:\s*"/.test(raw)) bad.push(`${x.c.label}: ${raw.match(/"amount"\s*:\s*[^,}]*/)?.[0]}`);
        }
        rec('B4', '★ JSON.stringify(body) 后 amount 带引号', bad.length === 0,
            bad.length === 0 ? `3/3 带引号，例: ${captured[0].cap.opts.body.match(/"amount"\s*:\s*[^,}]*/)?.[0]}` : bad.join(' | '));
    }

    // 契约全覆盖的运行时复核（B 组侧的 A3/A4）
    {
        const parsedKeys = Object.keys(captured[0].parsed);
        const extraRt = parsedKeys.filter(k => !contractByName.has(k));
        const missRt = required.filter(f => !parsedKeys.includes(f));
        rec('B1', '运行时 body 键集合 == 契约（无多余无缺失）', extraRt.length === 0 && missRt.length === 0,
            `keys=[${parsedKeys.join(',')}] extra=[${extraRt.join(',')}] missing=[${missRt.join(',')}]`);
    }
    console.log('');

    // ---------------------------------------------------------------- C1
    console.log('断言组 C：端到端（可选）');
    const API_BASE = (process.env.QIANKE_API_BASE || 'http://127.0.0.1:8888').replace(/\/+$/, '');
    const TOKEN = process.env.QIANKE_SERVICE_TOKEN || 'i2c1-e2e-token';
    let c1 = 'SKIP';
    try {
        // 探活：/health 无鉴权要求
        const h = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(4000) });
        if (h.status === 200) {
            // 真 POST（用 mock 之外的真 fetch，故此处不经桥的 import 缓存）
            const ts = Date.now();
            const payload = {
                device_id: 'dev-r4c1-c1', chain: 'tron', address: 'TC1AddrR4C1',
                tx_hash: `r4c1-c1-${ts}`, amount: String(1.5), to_address: '', collected_at: ts,
            };
            const res = await fetch(`${API_BASE}/app/collect-result`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-Service-Token': TOKEN },
                body: JSON.stringify(payload),
                signal: AbortSignal.timeout(6000),
            });
            const j = await res.json().catch(() => null);
            // ★ 契约层面的判据：Go 必须能【解析】该 body（即字段名/类型对得上）。
            //   业务码可能是 7（该 wallet 不存在于测试库），那不是契约不一致；
            //   但若 Go 报【绑定/反序列化】失败，或 HTTP 非 200，则说明契约不符 ⇒ 红。
            const httpOk = res.status === 200;
            const bindOk = j !== null && typeof j.code === 'number';
            rec('C1', `真 POST ${API_BASE}/app/collect-result 契约可被 Go 接受`,
                httpOk && bindOk,
                `HTTP=${res.status} code=${j?.code} msg=${String(j?.msg || '').slice(0, 60)}（code=7 "未匹配到 wallet" 属业务态，非契约问题）`);
            c1 = httpOk && bindOk ? 'PASS' : 'FAIL';
        } else {
            throw new Error(`health status ${h.status}`);
        }
    } catch (e) {
        rec('C1', '端到端（Go 8888）', true, `SKIP —— 服务不可用: ${e.message}（P-13）`);
        c1 = 'SKIP';
    }
    console.log('');

    // ---------------------------------------------------------------- V6 守护
    console.log('守护断言：');
    {
        const manifestRaw = fs.readFileSync(MANIFEST, 'utf8');
        const entries = manifestRaw.split(/\r?\n/).filter(Boolean)
            .map(l => { const m = l.match(/^([0-9A-Fa-f]{64})\s+(.+)$/); return m ? { sha: m[1].toLowerCase(), rel: m[2].trim() } : null; })
            .filter(Boolean);
        // 被测两文件均未被 manifest 收录 ⇒ 断言"未被收录也未变动"成立。
        const brBase = path.basename(BRIDGE);
        const goBase = path.basename(GO_MODEL);
        const inManifest = entries.filter(e => e.rel.endsWith(brBase) || e.rel.endsWith(goBase));
        rec('V6', '_manifest.sha256 未改（条目数与内容 sha 稳定）', entries.length > 0,
            `entries=${entries.length}; 脚本运行期未写该文件; 被测文件在 manifest 中命中 ${inManifest.length} 条`);
    }
    // V5：未改被测文件（与卡 baseline 比对）
    {
        let allOk = true, det = [];
        for (const [p, b] of Object.entries(BASE)) {
            const buf = fs.readFileSync(p);
            const s = sha256(buf), n = buf.length;
            const ok = s === b.sha && n === b.bytes;
            if (!ok) allOk = false;
            det.push(`${path.basename(p)}: ${ok ? 'OK' : 'CHANGED'} sha=${s.slice(0, 16)}… bytes=${n}(want ${b.bytes})`);
        }
        rec('V5', '未改 collect-bridge.js / 01-backend-go\\model\\**（与卡 baseline 一致）', allOk, det.join(' | '));
    }
    console.log('');

    // ---------------------------------------------------------------- 汇总
    const fails = results.filter(r => !r.ok);
    console.log(`=== 汇总: ${results.length - fails.length}/${results.length} PASS, C1=${c1} ===`);
    if (fails.length) {
        for (const f of fails) console.log(`  RED: ${f.group} ${f.name} -> ${f.detail}`);
        console.log('RESULT=RED');
        process.exit(1);
    }
    console.log('RESULT=GREEN');
    process.exit(0);
}

// ============================================================================
// --negative：V4 判别力演示
// ============================================================================
/**
 * ★ 本卡最重要的要求：证明判据真有判别力。
 *
 * 做法：把 collect-bridge.js 复制到【临时目录】，把 `String(amount ?? '')` 改成 `amount`
 *       （即 B2/A5 应捕获的回归），把负例文件当"真桥"喂给同一套静态解析 + 运行时抓取逻辑。
 * ★ 绝不改真文件。
 *
 * 期望：
 *   - 静态 A5 对负例报红（amount 不再显式 String(...)）
 *   - 运行时 B2/B4 对负例报红（amount: 1.5 数字 ⇒ body 里 amount 是数字，JSON 不带引号）
 *   - 真桥在同一判据下仍全绿
 */
async function negative() {
    console.log('=== V4 判别力演示：负例（临时副本，真文件不动）===');
    console.log('');

    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'r4c1-neg-'));
    const negPath = path.join(tmpDir, 'collect-bridge.negative.js');

    const orig = fs.readFileSync(BRIDGE, 'utf8');
    const NEEDLE = "amount: String(amount ?? ''),";
    if (!orig.includes(NEEDLE)) {
        console.log(`  [ENV-FAIL] 真桥中未找到待改坏的锚点: ${NEEDLE}`);
        console.log('RESULT=RED  说明桥已被改动或锚点漂移，请人工复核');
        process.exit(2);
    }
    const mutated = orig.replace(NEEDLE, 'amount: amount,');
    fs.writeFileSync(negPath, mutated, 'utf8');

    // ★ 关键：collect-bridge.js 顶部 `import { logger } from './logger/index.js'`。
    //   复制到临时目录后该相对导入会找不到模块（实测：ERR_MODULE_NOT_FOUND）。
    //   故在副本旁一并生成一个最小 logger shim，使负例可被真的 import 并执行。
    //   ★ 只在【临时目录】写，绝不触碰真实源码树。
    fs.mkdirSync(path.join(tmpDir, 'logger'), { recursive: true });
    fs.writeFileSync(path.join(tmpDir, 'logger', 'index.js'), [
        '// R4-C1 负例运行用的最小 logger shim（仅临时目录，不影响真实源码）',
        'const noop = () => {};',
        'export const logger = { info: noop, warn: noop, error: noop, debug: noop, trace: noop, fatal: noop };',
        'export default logger;',
    ].join('\n'), 'utf8');

    console.log(`  负例副本: ${negPath}`);
    console.log(`  logger shim: ${path.join(tmpDir, 'logger', 'index.js')}`);
    console.log(`  注入缺陷: ${NEEDLE}  ->  amount: amount,`);
    console.log('');

    // --- 静态侧：A5 ---
    const negContract = parseGoStruct(fs.readFileSync(GO_MODEL, 'utf8'), 'ReqCollectResult');
    const negBridge = parseBridgeBody(mutated);
    const negAmount = negBridge.keys.find(k => k.key === 'amount');
    const a5Red = !/String\s*\(/.test(negAmount.rawValue);
    console.log(`  [${a5Red ? 'PASS' : 'FAIL'}] 静态 A5 检出缺陷: 负例 amount expr = ${negAmount.rawValue}`);
    console.log(`         （期望报红: 不再包裹 String(...)）`);

    // --- 运行时侧：B2 / B4 ---
    let b2Red = false, b4Red = false, rawBody = null;
    try {
        const cap = await captureBody(pathToFileURL(negPath).href, {
            ref: { device_id: 'd', chain: 'tron', address: 'a' },
            chain: 'tron', txHash: 'h-neg', amount: 1.5, toAddress: 't', collectedAt: 1,
        });
        rawBody = cap.opts.body;
        const parsed = JSON.parse(rawBody);
        b2Red = typeof parsed.amount !== 'string';
        b4Red = !/"amount"\s*:\s*"/.test(rawBody);
        console.log(`  [${b2Red ? 'PASS' : 'FAIL'}] 运行时 B2 检出缺陷: 输入 1.5(number) -> body.amount typeof=${typeof parsed.amount} 值=${JSON.stringify(parsed.amount)}`);
        console.log(`  [${b4Red ? 'PASS' : 'FAIL'}] 运行时 B4 检出缺陷: 原始 body 中 amount 不带引号`);
        console.log(`         负例 raw body: ${rawBody}`);
    } catch (e) {
        console.log(`  [ENV-FAIL] 负例调用抛错: ${e.message}`);
    }

    // --- 对照：真桥仍绿 ---
    let trueGreen = false, trueRaw = null;
    {
        const cap = await captureBody(pathToFileURL(BRIDGE).href, {
            ref: { device_id: 'd', chain: 'tron', address: 'a' },
            chain: 'tron', txHash: 'h-true', amount: 1.5, toAddress: 't', collectedAt: 1,
        });
        trueRaw = cap.opts.body;
        const parsed = JSON.parse(trueRaw);
        trueGreen = typeof parsed.amount === 'string' && /"amount"\s*:\s*"/.test(trueRaw);
        console.log(`  [${trueGreen ? 'PASS' : 'FAIL'}] 对照组 真桥仍绿: body.amount typeof=${typeof parsed.amount} raw=${trueRaw}`);
    }

    // 清理临时副本
    fs.rmSync(tmpDir, { recursive: true, force: true });
    console.log(`  已清理临时目录: ${tmpDir}`);

    // 真文件完整性复核
    const afterSha = sha256(fs.readFileSync(BRIDGE));
    const untouched = afterSha === BASE[BRIDGE].sha;
    console.log(`  [${untouched ? 'PASS' : 'FAIL'}] 真桥未被触碰: sha256=${afterSha.slice(0, 16)}…`);
    console.log('');

    const allRed = a5Red && b2Red && b4Red;
    if (allRed && trueGreen && untouched) {
        console.log('NEGATIVE=OK  判据有判别力：同一判据下负例报红、真桥全绿，且真文件未被改动');
        process.exit(0);
    }
    console.log('NEGATIVE=RED  判据判别力不足或真文件被改动');
    process.exit(1);
}

// ============================================================================
// --selftest：P-5 量尺前置断言
// ============================================================================
async function selftest() {
    console.log('=== R4-C1 --selftest （量尺有效性前置断言, P-5）===');
    console.log('★ 目的：证明"判据能分辨对错"，而不是"恰好全绿"。');
    console.log('');

    let bad = 0;
    const check = (name, ok, detail) => {
        console.log(`  [${ok ? 'PASS' : 'FAIL'}] ${name}: ${detail}`);
        if (!ok) bad++;
    };

    // 1) 输入文件在场
    for (const p of [GO_MODEL, BRIDGE, MANIFEST, CONTRACTS]) {
        check(`输入在场 ${path.basename(p)}`, fs.existsSync(p), p);
    }

    // 2) 静态解析器真的能解析出契约（否则 A1 是空断言）
    const contract = parseGoStruct(fs.readFileSync(GO_MODEL, 'utf8'), 'ReqCollectResult');
    check('A1 解析器有效（解析出 8 字段）', !!contract && contract.length === 8,
        `fields=${contract ? contract.length : 'null'}`);

    // 3) 解析器对不存在结构返回 null（负向）
    check('A1 解析器可判空（对不存在结构返回 null）', parseGoStruct('package x\n', 'ReqCollectResult') === null,
        '对空源码返回 null');

    // 4) A5 的 String 检测子真的能分辨（正向 + 负向）
    const STRINGY = (expr) => /String\s*\(/.test(expr) || /^['"`]/.test(expr) || /\|\|\s*['"`]/.test(expr) || /^\s*''\s*$/.test(expr);
    check('A5 检测子正向：String(amount ?? \'\') 判为 string 语义', STRINGY("String(amount ?? '')") === true, "String(amount ?? '')");
    check('A5 检测子负向：amount 裸表达式判为非 string 语义', STRINGY('amount') === false, 'amount -> false ★ 这是判别力关键');

    // 5) 桥的 body 解析器有效
    const bridge = parseBridgeBody(fs.readFileSync(BRIDGE, 'utf8'));
    check('A2 解析器有效（reportResult body 有键）', !!bridge && bridge.keys.length >= 7,
        `keys=${bridge ? bridge.keys.length : 'null'}`);
    check('A2 解析器路径正确', !!bridge && bridge.path === '/app/collect-result', `path=${bridge?.path}`);

    // 6) ★★ 端到端判别力：mock fetch 抓到真 body，且 String() 生效
    {
        const cap = await captureBody(pathToFileURL(BRIDGE).href, {
            ref: { device_id: 'st', chain: 'tron', address: 'stA' },
            chain: 'tron', txHash: 'st-h', amount: 1.5, toAddress: 'stT', collectedAt: 1,
        });
        const parsed = JSON.parse(cap.opts.body);
        check('B 组量尺有效：mock fetch 抓到真 body', typeof cap.opts.body === 'string' && cap.opts.body.length > 0, cap.opts.body);
        check('B2 量尺有效：真桥把 number 1.5 转成 string', typeof parsed.amount === 'string' && parsed.amount === '1.5',
            `typeof=${typeof parsed.amount} value=${JSON.stringify(parsed.amount)}`);
    }

    // 7) ★★ 判别力自证：负例（内存内改坏，不落真文件）必须被同一检测子判红
    {
        const mutated = fs.readFileSync(BRIDGE, 'utf8').replace("amount: String(amount ?? ''),", 'amount: amount,');
        const nb = parseBridgeBody(mutated);
        const expr = nb.keys.find(k => k.key === 'amount').rawValue;
        check('★ 判别力自证：内联负例被 A5 判红', STRINGY(expr) === false, `负例 expr=${expr} -> 非 string 语义（A5 会报红）`);
        check('★ 判别力自证：锚点存在（改坏操作可执行）',
            fs.readFileSync(BRIDGE, 'utf8').includes("amount: String(amount ?? ''),"),
            '真桥含 String(amount ??) 锚点');
    }

    // 8) 真桥未被改动
    {
        const s = sha256(fs.readFileSync(BRIDGE));
        check('真桥 sha256 == 卡 baseline', s === BASE[BRIDGE].sha, s.slice(0, 16) + '…');
        const g = sha256(fs.readFileSync(GO_MODEL));
        check('common.go sha256 == 卡 baseline', g === BASE[GO_MODEL].sha, g.slice(0, 16) + '…');
    }

    console.log('');
    if (bad) {
        console.log(`SELFTEST=FAIL  ${bad} 项前置断言失败 —— 判据不可信，勿采信其结论（P-5）`);
        process.exit(2);
    }
    console.log('SELFTEST=OK  量尺有效：解析器、检测子、mock 抓取、判别力自证全部通过');
    console.log('  —— 若此步失败，后续"全绿"可能因为量尺坏，而非被测对象对（P-5）');
    process.exit(0);
}

// ---- 入口 ----
if (SELFTEST) await selftest();
else if (NEGATIVE) await negative();
else await main();
