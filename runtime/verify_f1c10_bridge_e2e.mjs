/**
 * F1-C10 判据：Node 桥端到端业务判据（P0-3 的回归保护）。
 *
 * ★ 真调用产物内的 collect-bridge.js，让它真的对 Go 发 HTTP。
 *   —— 不静态读源码冒充。
 *
 * 前置环境变量：
 *   QIANKE_API_BASE      = http://127.0.0.1:8888
 *   QIANKE_SERVICE_TOKEN = i2c1-e2e-token（与 Go config 的 app-jwt.service-token 一致）
 *
 * 用法：
 *   node verify_f1c10_bridge_e2e.mjs              # 全量
 *   node verify_f1c10_bridge_e2e.mjs --selftest   # 量尺前置断言（P-5）
 *
 * 退出码：0 = 全绿；非 0 = 有红。
 */
import { execFileSync } from 'node:child_process';
import path from 'node:path';

const MD_BIN = 'E:\\ios漏洞\\_integration\\_fix_work\\_toolchain\\mariadb-11.4.4-winx64\\bin';
const MYSQL = path.join(MD_BIN, 'mysql.exe');
const DB = 'qk_e2e';
const BRIDGE = 'file:///E:/USDT项目/02-backend-node/src_restored/core/collect-bridge.js';

const results = [];
function rec(name, ok, detail) {
    results.push({ name, ok: !!ok, detail });
    console.log(`  [${ok ? 'PASS' : 'FAIL'}] ${name}: ${detail}`);
}

function sql(stmt) {
    try {
        return execFileSync(MYSQL, ['--skip-ssl', '-h', '127.0.0.1', '-P', '13306',
            '-u', 'root', '--default-character-set=utf8mb4', '-B', '-e',
            `USE ${DB}; ${stmt}`], { encoding: 'utf-8' });
    } catch (e) {
        return String(e.stdout || e.message);
    }
}

function rows(stmt) {
    const out = sql(stmt);
    const lines = out.split('\n').map(l => l.trim()).filter(Boolean);
    return lines.slice(1).map(l => l.split('\t'));
}

// ★ WBE01-C：退出时把 wallet(1,2) 复位到夹具约定态（各脚本 cleanup 本就用这组值），
//   避免中途退出（异常/中断）把 wallet 留在改过的状态、污染同库其他判据。
function _walletReset() { sql("UPDATE wallet SET region = 0, progress = 0 WHERE id IN (1,2);"); }
process.on('exit', _walletReset);

function progressOf(walletId) {
    const r = rows(`SELECT progress FROM wallet WHERE id = ${walletId};`);
    return r.length ? String(r[0][0]) : null;
}

function setProgress(walletId, v) {
    sql(`UPDATE wallet SET progress = ${v} WHERE id = ${walletId};`);
}

const WALLET_ID = 1;

/**
 * 由 wallet 构造 bridge ref（device_id + chain + address）。
 *
 * ★ 关键（实测踩坑）：ref.device_id 必须是 **machine.device_id**（业务设备号，
 *   本环境为 `dev-e2e-001`），**不是** machine.id（数字 `1`）。
 *   wallet_resolver.go:48-52 的反查是
 *     `JOIN machine ON machine.id = wallet.machine_id
 *      WHERE machine.device_id = ? AND wallet.<col> = ?`
 *   ⇒ 传 machine.id 会得 `未匹配到 wallet`（code=7）。
 */
function walletRefOf(walletId) {
    const r = rows(
        `SELECT m.device_id, w.trx_address, w.eth_address ` +
        `FROM wallet w LEFT JOIN machine m ON m.id = w.machine_id WHERE w.id = ${walletId};`);
    if (!r.length) return null;
    return {
        device_id: r[0][0] || '',
        chain: 'tron',
        address: r[0][1] || r[0][2] || '',
    };
}

function cleanup() {
    sql("DELETE FROM bill WHERE transfer_hash LIKE 'i2c1-f1c10-%';");
    setProgress(WALLET_ID, 0);
    sql("UPDATE wallet SET region = 0 WHERE id = 1;");
}

async function main() {
    const argv = process.argv.slice(2);

    console.log('=== F1-C10 Node 桥端到端业务判据 ===');
    console.log(`桥: ${BRIDGE}`);
    console.log(`QIANKE_API_BASE=${process.env.QIANKE_API_BASE || '(未设置)'}`);
    console.log(`QIANKE_SERVICE_TOKEN=${process.env.QIANKE_SERVICE_TOKEN ? '(已设置)' : '(未设置)'}`);
    console.log('');

    const b = await import(BRIDGE);
    const { bridgeEnabled, shouldCollect, acquireLock, releaseLock, reportResult } = b;

    // ---- 前置断言（P-5）----
    console.log('前置断言:');
    if (!bridgeEnabled()) {
        console.log('  [FAIL] bridgeEnabled() === false —— 桥会短路返回，断言无意义');
        console.log('         需设置 QIANKE_API_BASE 与 QIANKE_SERVICE_TOKEN');
        console.log('RESULT=RED');
        process.exit(1);
    }
    console.log('  [PASS] bridgeEnabled() === true');

    // Go 服务就绪
    try {
        const r = await fetch((process.env.QIANKE_API_BASE || '') + '/health');
        if (r.status !== 200) throw new Error(`status ${r.status}`);
        console.log('  [PASS] Go /health 200');
    } catch (e) {
        console.log(`  [FAIL] Go 服务不可达: ${e.message}`);
        console.log('RESULT=RED');
        process.exit(1);
    }

    cleanup();
    const ref = walletRefOf(WALLET_ID);
    console.log(`  ref = ${JSON.stringify(ref)}`);
    console.log('');

    // ★ 量尺有效性（在正式断言之前）：业务成功必须能返回 ok=true
    {
        setProgress(WALLET_ID, 0);
        const ts = Date.now();
        const r = await reportResult({
            ref, chain: 'tron', txHash: `i2c1-f1c10-selftest-${ts}`,
            amount: '100', toAddress: '', collectedAt: ts,
        });
        if (r.ok === true) {
            console.log(`  [PASS] 量尺有效：合法归集返回 ok=true（code=${r.json?.code}）`);
        } else {
            console.log(`  [FAIL] 量尺无效：合法归集竟返回 ok=${r.ok}（code=${r.json?.code}）`);
            console.log('RESULT=RED');
            process.exit(1);
        }
    }
    cleanup();

    if (argv.includes('--selftest')) {
        console.log('');
        console.log('SELFTEST=OK  （量尺有效：合法归集返回 ok=true，说明写入通道与鉴权均正常）');
        console.log('  —— 若此步失败，"ok=false" 可能因为环境坏，而非桥判对了（P-5）');
        process.exit(0);
    }

    console.log('');
    console.log('正式断言:');
    const ts = Date.now();

    // ---- B1: reportResult 业务成功 ----
    {
        setProgress(WALLET_ID, 0);
        const h = `i2c1-f1c10-B1-${ts}`;
        const r = await reportResult({ ref, chain: 'tron', txHash: h, amount: '100', toAddress: '', collectedAt: ts });
        rec('B1 reportResult 业务成功 -> ok=true', r.ok === true,
            `ok=${r.ok} HTTP=${r.status} code=${r.json?.code} billId=${r.json?.data?.billId}`);
    }

    // ---- B2: ★ 业务失败（负金额，F1-C8 拒绝）-> 桥必须 ok=false ----
    {
        const h = `i2c1-f1c10-B2-${ts}`;
        const r = await reportResult({ ref, chain: 'tron', txHash: h, amount: '-5', toAddress: '', collectedAt: ts });
        // 反例对照：HTTP 200 但 code != 0 —— 这正是 P0-3 的逃逸形态
        const httpOk = r.status === 200;
        const bizFail = r.json?.code !== 0;
        rec('B2 负金额 -> 桥判失败 (ok=false)', r.ok === false,
            `ok=${r.ok} HTTP=${r.status} code=${r.json?.code} msg=${r.json?.msg}`);
        rec('B2 反例对照：HTTP 200 但 code!=0（只用 r.ok 会 fail-open）',
            httpOk && bizFail,
            `HTTP=${r.status} code=${r.json?.code} ⇒ 若判据是 r.ok 则误判为成功`);
        const n = rows(`SELECT COUNT(*) FROM bill WHERE transfer_hash='${h}';`);
        rec('B2 且不落账', n.length && n[0][0] === '0', `bill=${n[0]?.[0]}`);
    }

    // ---- B3: ★ 业务失败（to_address 不符，F1-C9 拒绝）----
    {
        const h = `i2c1-f1c10-B3-${ts}`;
        const r = await reportResult({ ref, chain: 'tron', txHash: h, amount: '100', toAddress: 'TOTALLY_WRONG', collectedAt: ts });
        rec('B3 to_address 不符 -> 桥判失败 (ok=false)', r.ok === false,
            `ok=${r.ok} HTTP=${r.status} code=${r.json?.code} msg=${(r.json?.msg || '').slice(0, 70)}`);
        const n = rows(`SELECT COUNT(*) FROM bill WHERE transfer_hash='${h}';`);
        rec('B3 且不落账', n.length && n[0][0] === '0', `bill=${n[0]?.[0]}`);
    }

    // ---- B4: 词表外 chain ----
    {
        const h = `i2c1-f1c10-B4-${ts}`;
        const r = await reportResult({ ref, chain: 'sol', txHash: h, amount: '100', toAddress: '', collectedAt: ts });
        rec('B4 词表外 chain -> 桥判失败 (ok=false)', r.ok === false,
            `ok=${r.ok} HTTP=${r.status} code=${r.json?.code}`);
    }

    // ---- B5: shouldCollect progress=0 -> true ----
    {
        setProgress(WALLET_ID, 0);
        const v = await shouldCollect(ref);
        rec('B5 shouldCollect (progress=0) -> true', v === true, `returned=${v}`);
    }

    // ---- B6: ★ shouldCollect progress=1 -> false（不双重归集）----
    {
        setProgress(WALLET_ID, 1);
        const v = await shouldCollect(ref);
        rec('B6 shouldCollect (progress=1) -> false', v === false,
            `returned=${v}  ← 潜客正在收割，桥须保守跳过`);
    }

    // ---- B7: acquireLock 成功且 DB progress 变 1 ----
    {
        setProgress(WALLET_ID, 0);
        const ok = await acquireLock(ref);
        const p = progressOf(WALLET_ID);
        rec('B7 acquireLock 成功且 DB progress=1', ok === true && p === '1',
            `acquireLock=${ok} DB.progress=${p}`);
    }

    // ---- B8: ★ acquireLock 冲突（已占用）-> false ----
    {
        // progress 已为 1（B7 留下的），再占一次应冲突
        setProgress(WALLET_ID, 1);
        const ok = await acquireLock(ref);
        rec('B8 acquireLock 冲突 -> false', ok === false,
            `acquireLock=${ok}  ← 已占用，桥须保守跳过`);
        await releaseLock(ref);
    }

    cleanup();
    console.log('');
    const fails = results.filter((r) => !r.ok);
    console.log(`=== ${results.length - fails.length}/${results.length} 通过 ===`);
    console.log('');
    console.log('★ 覆盖声明：');
    console.log('  - 已覆盖：桥与 Go 的【业务契约一致性】（code!=0 ⇒ 桥判失败），含 fail-closed 与互斥。');
    console.log('  - 未覆盖：链上归集正确性、collect-task/确认链（W2-C6 范围）、真机/真链。');
    console.log('    ⇒ 本卡验证的是「桥与 Go 的契约」，不是「链上归集」；后者按 V0 D-4 永久未授权。');

    if (fails.length) {
        console.log(`RESULT=RED  ${fails.length} 项失败`);
        for (const f of fails) console.log(`  - ${f.name}: ${f.detail}`);
        process.exit(1);
    }
    console.log('RESULT=GREEN  桥在业务失败时正确判失败（P0-3 回归保护建立）');
    process.exit(0);
}

main().catch((e) => {
    console.log(`[FATAL] ${e.stack || e.message}`);
    process.exit(1);
});
