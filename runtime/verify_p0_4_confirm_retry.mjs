#!/usr/bin/env node
// ============================================================================
// verify_p0_4_confirm_retry.mjs  —— W2-C6 (P0-4) 行为判据（stub 驱动）
// ============================================================================
// 判据（先在动实现之前跑到【红】，再动实现跑到【绿】）：
//   R1  reportResult 返回【业务失败】(code != 0)
//        ⇒ log 仍 pending / 未置 confirmed / 地址未被重置 idle / 写入了重试标记
//   R2  reportResult 返回【业务成功】(code === 0)
//        ⇒ log 置 confirmed；且【该地址全部 log 均成功】时才重置 idle（防改过头）
//   R3  连续失败达上限
//        ⇒ 达上限后有【显式 error 告警】且【不再无限重试】（防改成死循环）
//
// 桩（必须用桩，不得依赖真实链 / 真实潜客）：
//   被测文件依赖的 7 个模块（logger / 两个 model / 三个 chain collector / collect-bridge）
//   以 data: URL 形式注入（**零磁盘写入**），仅把真实文件的 import 说明符机械改写为这些
//   data: URL —— 被测逻辑本身逐字节未动（脚本内自带「可逆性」证明）。
//
// P-4：本判据件放产物外（E:\ios漏洞\_integration\_fix_work\），不在 E:\USDT项目 产物树内。
// ============================================================================
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';

const TARGET = 'E:\\USDT项目\\02-backend-node\\src_restored\\schedules\\collect-confirm-task.js';

// ---------------------------------------------------------------------------
// 0. 可控时钟（仅用于 R3 的退避窗口推进；真实 Date 语义不受影响）
// ---------------------------------------------------------------------------
const realNow = Date.now.bind(Date);
Date.now = () => (globalThis.__W2C6__ && typeof globalThis.__W2C6__.now === 'number')
    ? globalThis.__W2C6__.now : realNow();

// ---------------------------------------------------------------------------
// 1. 桩模块源码（data: URL 注入；均通过 globalThis.__W2C6__ 共享状态）
// ---------------------------------------------------------------------------
const DATA = (src) => 'data:text/javascript;charset=utf-8,' + encodeURIComponent(src);

const STUB_LOGGER = `
const S = () => globalThis.__W2C6__;
export const logger = {
  info: (...a) => S().info.push(a),
  warn: (...a) => S().warn.push(a),
  error: (...a) => S().error.push(a),
  debug: (...a) => S().debug.push(a),
  trace: () => {},
  fatal: (...a) => S().error.push(a),
};
`;

const STUB_COLLECT_LOG = `
const S = () => globalThis.__W2C6__;
const clone = (o) => JSON.parse(JSON.stringify(o));
export const CollectLog = {
  find(filter) {
    const f = filter || {};
    const rows = S().logs
      .filter((l) => f.status === undefined || l.status === f.status)
      .map(clone);
    return { limit: (n) => ({ lean: async () => rows.slice(0, n) }), lean: async () => rows };
  },
  async updateOne(filter, update) {
    S().logUpdates.push({ filter, update });
    const l = S().logs.find((x) => String(x._id) === String(filter._id));
    if (l) {
      if (update.$set) Object.assign(l, update.$set);
      if (update.$push && update.$push.attempts)
        (l.attempts = l.attempts || []).push(update.$push.attempts);
      if (update.$inc) for (const k in update.$inc) l[k] = (l[k] || 0) + update.$inc[k];
    }
    return { acknowledged: true, modifiedCount: l ? 1 : 0 };
  },
  async exists(filter) {
    const f = filter || {};
    const hit = S().logs.some((l) =>
      (f.status === undefined || l.status === f.status) &&
      (f.addressId === undefined || String(l.addressId) === String(f.addressId)));
    return hit ? { _id: 'exists' } : null;
  },
};
`;

const STUB_DERIVED = `
const S = () => globalThis.__W2C6__;
export const DerivedAddress = {
  async updateOne(filter, update) {
    S().addrUpdates.push({ filter, update });
    const a = S().addresses[String(filter._id)];
    let modified = 0;
    if (a) {
      const cs = filter.collectStatus;
      const match = cs === undefined ? true
        : typeof cs === 'string' ? a.collectStatus === cs
          : (cs && Array.isArray(cs.$in) ? cs.$in.includes(a.collectStatus) : true);
      if (match) {
        if (update.$set) Object.assign(a, update.$set);
        if (update.$inc) for (const k in update.$inc) a[k] = (a[k] || 0) + update.$inc[k];
        modified = 1;
      }
    }
    return { acknowledged: true, modifiedCount: modified };
  },
  async updateMany() { return { acknowledged: true, modifiedCount: 0 }; },
  find() { return { lean: async () => [] }; },
};
`;

const stubChain = `
const S = () => globalThis.__W2C6__;
export async function getTransactionStatus(hash, createdAt) {
  S().chainCalls.push({ hash, createdAt });
  const m = S().chainStatusByHash || {};
  return { status: (hash in m) ? m[hash] : S().chainStatus };
}
`;

const STUB_BRIDGE = `
const S = () => globalThis.__W2C6__;
export function walletRef(doc) {
  return { device_id: (doc && doc.deviceId) || '', chain: (doc && doc.chain) || '', address: (doc && doc.address) || '' };
}
export function bridgeEnabled() { return true; }
export async function shouldCollect() { return true; }
export async function acquireLock() { return true; }
export async function releaseLock(ref) { S().releaseCalls.push(ref); }
export async function reportResult(args) {
  S().reportCalls.push(args);
  const q = S().reportQueue;
  if (Array.isArray(q) && q.length) return q.shift();
  if (typeof S().reportResult === 'function') return S().reportResult(args);
  return { ok: true, status: 200, json: { code: 0, data: {} } };
}
`;

const STUBS = [
    ["'../core/logger/index.js'", DATA(STUB_LOGGER)],
    ["'../core/db/models/collect-log.js'", DATA(STUB_COLLECT_LOG)],
    ["'../core/db/models/derived-address.js'", DATA(STUB_DERIVED)],
    ["'../core/collect/eth-collector.js'", DATA(stubChain)],
    ["'../core/collect/tron-collector.js'", DATA(stubChain)],
    ["'../core/collect/btc-collector.js'", DATA(stubChain)],
    ["'../core/collect-bridge.js'", DATA(STUB_BRIDGE)],
];

// ---------------------------------------------------------------------------
// 2. 读真实文件 + 机械改写 import 说明符（带可逆性证明）
// ---------------------------------------------------------------------------
let SRC;
try {
    SRC = readFileSync(TARGET, 'utf8');
} catch (e) {
    console.log('FATAL: 读不到被测文件 ' + TARGET + ' -> ' + e.message);
    process.exit(2);
}
const SRC_SHA = createHash('sha256').update(Buffer.from(SRC, 'utf8')).digest('hex');

let REWRITTEN = SRC;
for (const [spec, url] of STUBS) {
    if (!REWRITTEN.includes(spec)) {
        console.log('FATAL: 被测文件缺少预期 import 说明符 ' + spec);
        process.exit(2);
    }
    REWRITTEN = REWRITTEN.replace(spec, JSON.stringify(url));
}
// 可逆性证明：把注入的 URL 还原回原说明符，必须与原文逐字节相同
let REVERTED = REWRITTEN;
for (const [spec, url] of STUBS) REVERTED = REVERTED.replace(JSON.stringify(url), spec);
const REVERSIBLE = REVERTED === SRC;

// ---------------------------------------------------------------------------
// 3. 微型断言框架
// ---------------------------------------------------------------------------
let FAILS = 0;
let CHECKS = 0;
function chk(tag, name, cond, detail) {
    CHECKS++;
    if (!cond) FAILS++;
    console.log('  [' + tag + '] ' + (cond ? 'PASS' : 'FAIL') + ' | ' + name
        + (detail === undefined ? '' : ' | ' + detail));
}

// ---------------------------------------------------------------------------
// 4. 夹具 / 载入
// ---------------------------------------------------------------------------
function mkLog(id, addressId, over) {
    return Object.assign({
        _id: id, addressId, address: '0xSRC' + id, chain: 'eth', token: 'usdt',
        amount: '10', targetAddress: '0xTGT' + id, txHash: '0xHASH' + id,
        deviceId: 'dev1', status: 'pending', attempts: [],
        createdAt: new Date(realNow() - 1000),
    }, over || {});
}

async function loadFresh(tag) {
    return await import('data:text/javascript;charset=utf-8,'
        + encodeURIComponent(REWRITTEN) + '#' + tag);
}

function baseState(logs, addresses) {
    return {
        logs, addresses, now: realNow(),
        info: [], warn: [], error: [], debug: [],
        reportCalls: [], releaseCalls: [], chainCalls: [],
        logUpdates: [], addrUpdates: [],
        chainStatus: 'confirmed', chainStatusByHash: {}, reportQueue: [], reportResult: null,
    };
}

const OK_RESULT = { ok: true, status: 200, json: { code: 0, data: { billId: 'b1' } } };
const FAIL_RESULT = { ok: false, status: 200, json: { code: 7, msg: '未落账 / 查询失败' } };

// ---------------------------------------------------------------------------
console.log('=== verify_p0_4_confirm_retry (W2-C6 / R3 行为判据) ===');
console.log('被测件 : ' + TARGET);
console.log('sha256 : ' + SRC_SHA + '  (' + Buffer.byteLength(SRC, 'utf8') + ' B, 读于 ' + new Date().toISOString() + ')');
console.log('改写可逆性证明: ' + (REVERSIBLE ? 'PASS（注入 data:URL 还原后与原文逐字节相同）'
    : 'FAIL（改写不限于 import 说明符！）'));
CHECKS++; if (!REVERSIBLE) FAILS++;
console.log('');

// ============================== R1 ========================================
{
    console.log('--- R1: reportResult 业务失败 -> 保持 pending / 未 confirmed / 地址未重置 idle / 有重试标记 ---');
    const st = baseState([mkLog('L1', 'A1')], { A1: { _id: 'A1', collectStatus: 'collected' } });
    st.reportQueue = [FAIL_RESULT];
    globalThis.__W2C6__ = st;
    const mod = await loadFresh('R1');
    await mod.collectConfirmTask.handler();

    chk('R1', 'log 仍为 pending（未被置 confirmed）', st.logs[0].status === 'pending', 'status=' + st.logs[0].status);
    chk('R1', 'confirmedAt 未写入', st.logs[0].confirmedAt === undefined, 'confirmedAt=' + String(st.logs[0].confirmedAt));
    chk('R1', '地址未被重置为 idle', st.addresses.A1.collectStatus === 'collected', 'collectStatus=' + st.addresses.A1.collectStatus);
    const idleWrites = st.addrUpdates.filter((u) => u.update && u.update.$set && u.update.$set.collectStatus === 'idle');
    chk('R1', '没有任何「重置 idle」的地址写', idleWrites.length === 0, 'idle-writes=' + idleWrites.length);
    chk('R1', '写入了重试标记（attempts 增长）', Array.isArray(st.logs[0].attempts) && st.logs[0].attempts.length >= 1,
        'attempts=' + JSON.stringify(st.logs[0].attempts));
    const pushOk = st.logUpdates.some((u) => u.update && u.update.$push && u.update.$push.attempts);
    chk('R1', '重试标记经由 $push attempts 落盘', pushOk, 'logUpdates=' + st.logUpdates.length);
    chk('R1', '回传确实被调用了一次（失败路径真的走到了回传）', st.reportCalls.length === 1, 'reportCalls=' + st.reportCalls.length);
    console.log('');
}

// ============================== R2 ========================================
{
    console.log('--- R2a: reportResult 业务成功 -> 置 confirmed；该地址全部 log 成功 -> 重置 idle ---');
    const st = baseState([mkLog('L1', 'A1')], { A1: { _id: 'A1', collectStatus: 'collected' } });
    st.reportQueue = [OK_RESULT];
    globalThis.__W2C6__ = st;
    const mod = await loadFresh('R2a');
    await mod.collectConfirmTask.handler();

    chk('R2a', 'log 置 confirmed', st.logs[0].status === 'confirmed', 'status=' + st.logs[0].status);
    chk('R2a', 'confirmedAt 已写入', st.logs[0].confirmedAt instanceof Date, 'confirmedAt=' + String(st.logs[0].confirmedAt));
    chk('R2a', '无重试标记（成功不该记 attempts）', (st.logs[0].attempts || []).length === 0,
        'attempts=' + JSON.stringify(st.logs[0].attempts));
    chk('R2a', '全部 log 成功 -> 地址重置 idle', st.addresses.A1.collectStatus === 'idle', 'collectStatus=' + st.addresses.A1.collectStatus);

    console.log('--- R2b: 同地址另有「链上未确认」的 log -> 不得重置 idle（防改过头）---');
    const st2 = baseState(
        [mkLog('L1', 'A1'), mkLog('L2', 'A1')],
        { A1: { _id: 'A1', collectStatus: 'collected' } });
    // L1 链上已确认且回传成功；L2 链上仍未确认（保持 pending）⇒ 地址不得被重置。
    st2.chainStatusByHash = { '0xHASHL1': 'confirmed', '0xHASHL2': 'pending' };
    st2.reportQueue = [OK_RESULT, OK_RESULT];
    globalThis.__W2C6__ = st2;
    const mod2 = await loadFresh('R2b');
    await mod2.collectConfirmTask.handler();

    chk('R2b', 'L1 置 confirmed', st2.logs[0].status === 'confirmed', 'L1.status=' + st2.logs[0].status);
    chk('R2b', 'L2 仍 pending', st2.logs[1].status === 'pending', 'L2.status=' + st2.logs[1].status);
    chk('R2b', '地址未被重置 idle（尚有 pending）', st2.addresses.A1.collectStatus === 'collected',
        'collectStatus=' + st2.addresses.A1.collectStatus);
    const idleWrites2 = st2.addrUpdates.filter((u) => u.update && u.update.$set && u.update.$set.collectStatus === 'idle');
    chk('R2b', '没有「重置 idle」的地址写', idleWrites2.length === 0, 'idle-writes=' + idleWrites2.length);
    console.log('');
}

// ============================== R3 ========================================
{
    console.log('--- R3: 连续失败达上限 -> 有显式 error 告警 且 不再无限重试 ---');
    const st = baseState([mkLog('L1', 'A1')], { A1: { _id: 'A1', collectStatus: 'collected' } });
    st.reportQueue = [];                 // 队列空 -> 用 reportResult 常量失败
    st.reportResult = () => FAIL_RESULT; // 永远失败
    globalThis.__W2C6__ = st;

    const mod = await loadFresh('R3');
    const MAX = Number.isInteger(mod.REPORT_MAX_ATTEMPTS) ? mod.REPORT_MAX_ATTEMPTS : 5;
    const BACKOFF = Number.isInteger(mod.REPORT_RETRY_BACKOFF_MS) ? mod.REPORT_RETRY_BACKOFF_MS : 60000;
    const ITER = MAX + 5;
    const t0 = realNow();
    for (let i = 0; i < ITER; i++) {
        st.now = t0 + (i + 1) * (BACKOFF + 60000); // 每轮越过一个退避窗口
        await mod.collectConfirmTask.handler();
    }

    chk('R3', '上限常量存在且为有限正整数', Number.isInteger(mod.REPORT_MAX_ATTEMPTS) && mod.REPORT_MAX_ATTEMPTS > 0
        && mod.REPORT_MAX_ATTEMPTS <= 20, 'REPORT_MAX_ATTEMPTS=' + String(mod.REPORT_MAX_ATTEMPTS));
    chk('R3', '退避常量存在', Number.isInteger(mod.REPORT_RETRY_BACKOFF_MS) && mod.REPORT_RETRY_BACKOFF_MS > 0,
        'REPORT_RETRY_BACKOFF_MS=' + String(mod.REPORT_RETRY_BACKOFF_MS));
    chk('R3', '回传次数被上限截断（不再无限重试）', st.reportCalls.length === MAX,
        'reportCalls=' + st.reportCalls.length + ' (期望 MAX=' + MAX + ', 迭代 ' + ITER + ' 轮)');
    const errHit = st.error.filter((a) => String(a[1] || '').includes('上限') || String(a[1] || '').includes('limit')
        || String(a[1] || '').includes('告警'));
    chk('R3', '达上限有显式 error 告警', errHit.length >= 1,
        'errorCalls=' + st.error.length + ' / 命中上限告警=' + errHit.length);
    chk('R3', '达上限后 log 仍为 pending（未被误置 confirmed）', st.logs[0].status === 'pending', 'status=' + st.logs[0].status);
    chk('R3', '重试标记条数 == 实际上限', (st.logs[0].attempts || []).length === MAX,
        'attempts=' + (st.logs[0].attempts || []).length);
    console.log('');
}

// ---------------------------------------------------------------------------
console.log('=== 汇总: ' + (CHECKS - FAILS) + '/' + CHECKS + ' 通过, 失败 ' + FAILS + ' ===');
process.exit(FAILS === 0 ? 0 : 1);
