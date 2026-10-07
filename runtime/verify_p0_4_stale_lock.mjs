#!/usr/bin/env node
// ============================================================================
// W2-C7 (P0-4 b2) 判据脚本：崩溃残留占位的「同实例自证」回收
//   放产物外（_fix_work）—— P-4：判据放产物内会自泄。
//   桩驱动，不依赖真实崩溃（真实「杀进程再重启」不可复现、不可在 CI 跑）。
//
// ★ 被测件 = 产物件的【逐字节副本】（沙箱 _sandbox 内，sha 与产物件逐一相等）。
//   本脚本只从沙箱 import；产物件本体另由 `node --check`(0) + sha 同一双重覆盖。
//
// 退出码：0 = 全绿；2 = RED（判据函数尚未导出 / 模块加载失败）；3 = 量尺自检坏；
//         1 = 断言失败
// ============================================================================
import { pathToFileURL } from 'node:url';
import path from 'node:path';

const SANDBOX = process.env.W2C7_SANDBOX || 'E:/_dispatch/W2-C7/_sandbox';
const url = (rel) => pathToFileURL(path.join(SANDBOX, rel)).href;

let failed = 0;
let passed = 0;
const line = (s) => process.stdout.write(s + '\n');
function check(name, cond, detail = '') {
    if (cond) {
        passed++;
        line(`  PASS  ${name}${detail ? '  [' + detail + ']' : ''}`);
    } else {
        failed++;
        line(`  FAIL  ${name}${detail ? '  [' + detail + ']' : ''}`);
    }
}
const mkLogger = () => ({ warn: [], info: [], error: [], debug: [] });
const loggerSink = (bag) => ({
    warn: (...a) => bag.warn.push(a),
    info: (...a) => bag.info.push(a),
    error: (...a) => bag.error.push(a),
    debug: (...a) => bag.debug.push(a),
});

line('=== W2-C7 verify_p0_4_stale_lock ===');
line(`sandbox = ${SANDBOX}`);

// ---------------------------------------------------------------------------
// 加载被测件（沙箱副本）
// ---------------------------------------------------------------------------
let m;
let bridge;
let da;
try {
    m = await import(url('schedules/collect-task.js'));
    bridge = await import(url('core/collect-bridge.js'));
    da = await import(url('core/db/models/derived-address.js'));
}
catch (e) {
    line(`RED: 沙箱模块加载失败 -> ${e?.message || e}`);
    process.exit(2);
}

const missing = ['shouldReclaim', 'isStaleCollecting', 'recoverStuckDocs', 'warnStaleCollecting']
    .filter((k) => typeof m[k] !== 'function');
if (missing.length > 0) {
    line(`RED: 判据函数尚未导出 -> [${missing.join(', ')}]（W2-C7 实现前，预期如此）`);
    process.exit(2);
}

const HOUR = 60 * 60 * 1000;
const NOW = Date.now();

// ---------------------------------------------------------------------------
// ★ 量尺前置断言（P-5）：先用【必然命中】的样本证明量尺能命中；
//   命中为 0 时先怀疑量尺坏了，不是数据没有。任何一条不过 ⇒ 量尺坏，退出码 3。
// ---------------------------------------------------------------------------
line('--- 量尺自检（必须先全过） ---');
{
    const selfDoc = { collectStatus: 'collecting', collectOwner: '9' };
    const otherDoc = { collectStatus: 'collecting', collectOwner: '1' };
    const staleDoc = { _id: 'pc', chain: 'eth', collectStatus: 'collecting', collectOwner: '1', collectingAt: new Date(NOW - 9 * HOUR) };
    const freshDoc = { _id: 'pc2', chain: 'eth', collectStatus: 'collecting', collectOwner: '1', collectingAt: new Date(NOW - 1 * HOUR) };
    const r5 = m.shouldReclaim(selfDoc, '9') === true;
    const r6 = m.shouldReclaim(otherDoc, '9') === false;
    const bag = mkLogger();
    const hit = await m.warnStaleCollecting([staleDoc], { logger: loggerSink(bag), now: NOW });
    const bag2 = mkLogger();
    const miss = await m.warnStaleCollecting([freshDoc], { logger: loggerSink(bag2), now: NOW });
    const r7 = hit === 1 && bag.warn.length === 1;
    const r8 = miss === 0 && bag2.warn.length === 0;
    check('PC1 shouldReclaim(own)=true', r5);
    check('PC2 shouldReclaim(other)=false', r6);
    check('PC3 已知 stale 样本必命中 1 条 warn', r7, `warned=${hit}`);
    check('PC4 已知 fresh 样本必 0 warn', r8, `warned=${miss}`);
    check('PC5 STALE_COLLECTING_MS === 4h', m.STALE_COLLECTING_MS === 4 * HOUR, `got=${m.STALE_COLLECTING_MS}`);
    if (failed > 0) {
        line('量尺自检未过 -> 量尺坏，停止（退出码 3）');
        process.exit(3);
    }
}

// ---------------------------------------------------------------------------
// S1..S5（桩驱动）
// ---------------------------------------------------------------------------
line('--- S1..S5 桩驱动 ---');

// S1: 自身崩溃残留 -> 释放 1 次 + 复位 idle
{
    const doc = { _id: 'S1', chain: 'eth', address: '0xS1', deviceId: 'd1', collectStatus: 'collecting', collectOwner: '3', collectingAt: new Date(NOW - 10 * 60 * 1000) };
    const rel = []; const rst = []; const bag = mkLogger();
    const sum = await m.recoverStuckDocs([doc], {
        instanceId: '3',
        releaseLock: async (r) => { rel.push(r); },
        logger: loggerSink(bag),
        walletRef: bridge.walletRef,
        resetToIdle: async (d) => { rst.push(d._id); d.collectStatus = 'idle'; d.collectOwner = ''; },
    });
    line(`S1 out: ${JSON.stringify({ summary: sum, releaseCalls: rel.length, ref: rel[0] || null, resetIds: rst, status: doc.collectStatus, owner: doc.collectOwner, warns: bag.warn.length })}`);
    check('S1 releaseLock 被调用恰 1 次', rel.length === 1, `got=${rel.length}`);
    check('S1 ref 指向该 doc（address=0xS1）', rel[0]?.address === '0xS1');
    check('S1 doc 复位为 idle', doc.collectStatus === 'idle', `got=${doc.collectStatus}`);
    check('S1 doc 清空 collectOwner', doc.collectOwner === '', `got='${doc.collectOwner}'`);
    check('S1 summary.reclaimed===1', sum.reclaimed === 1);
}

// S2: 活着的对端 -> 一次都不释放，且不改 collectStatus
{
    const doc = { _id: 'S2', chain: 'eth', address: '0xS2', deviceId: 'd2', collectStatus: 'collecting', collectOwner: '7', collectingAt: new Date(NOW - 10 * 60 * 1000) };
    const rel = []; const rst = []; const bag = mkLogger();
    const sum = await m.recoverStuckDocs([doc], {
        instanceId: '3',
        releaseLock: async (r) => { rel.push(r); },
        logger: loggerSink(bag),
        walletRef: bridge.walletRef,
        resetToIdle: async (d) => { rst.push(d._id); },
    });
    line(`S2 out: ${JSON.stringify({ summary: sum, releaseCalls: rel.length, resetIds: rst, status: doc.collectStatus, owner: doc.collectOwner, warns: bag.warn.length })}`);
    check('S2 releaseLock 一次都没被调用', rel.length === 0, `got=${rel.length}`);
    check('S2 resetToIdle 未被调用', rst.length === 0, `got=${rst.length}`);
    check('S2 doc.collectStatus 未被改动（仍 collecting）', doc.collectStatus === 'collecting', `got=${doc.collectStatus}`);
    check('S2 未产生 warn', bag.warn.length === 0);
}

// S3: 空 collectOwner（存量）-> 不释放 + 1 条 warn
{
    const doc = { _id: 'S3', chain: 'tron', address: 'TS3', deviceId: 'd3', collectStatus: 'collecting', collectOwner: '' };
    const rel = []; const rst = []; const bag = mkLogger();
    const sum = await m.recoverStuckDocs([doc], {
        instanceId: '3',
        releaseLock: async (r) => { rel.push(r); },
        logger: loggerSink(bag),
        walletRef: bridge.walletRef,
        resetToIdle: async (d) => { rst.push(d._id); },
    });
    line(`S3 out: ${JSON.stringify({ summary: sum, releaseCalls: rel.length, resetIds: rst.length, status: doc.collectStatus, warns: bag.warn.length, warnMsg: bag.warn[0]?.[1] || null })}`);
    check('S3 releaseLock 未被调用', rel.length === 0, `got=${rel.length}`);
    check('S3 resetToIdle 未被调用', rst.length === 0, `got=${rst.length}`);
    check('S3 doc.collectStatus 未被改动', doc.collectStatus === 'collecting', `got=${doc.collectStatus}`);
    check('S3 产生恰 1 条 warn', bag.warn.length === 1, `got=${bag.warn.length}`);
}

// S4: collectingAt 早于 4h -> 1 条 warn 且 releaseLock 未被调用（告警只报警不动手）
{
    const doc = { _id: 'S4', chain: 'eth', address: '0xS4', deviceId: 'd4', collectStatus: 'collecting', collectOwner: '7', collectingAt: new Date(NOW - 5 * HOUR) };
    const rel = []; const bag = mkLogger();
    // 先跑回收分派（此 doc 属异己持有者 -> 保持现状），再跑告警路径；全程共用同一 releaseLock 记录器。
    await m.recoverStuckDocs([doc], {
        instanceId: '3',
        releaseLock: async (r) => { rel.push(r); },
        logger: loggerSink(bag),
        walletRef: bridge.walletRef,
        resetToIdle: async () => { throw new Error('S4 不应复位'); },
    });
    const warned = await m.warnStaleCollecting([doc], { logger: loggerSink(bag), now: NOW });
    line(`S4 out: ${JSON.stringify({ warned, releaseCalls: rel.length, status: doc.collectStatus, warns: bag.warn.length, warnMsg: bag.warn[0]?.[1] || null })}`);
    check('S4 产生恰 1 条 warn', bag.warn.length === 1, `got=${bag.warn.length}`);
    check('S4 warn 载荷含 addressId=S4', bag.warn[0]?.[0]?.addressId === 'S4');
    check('S4 warn 载荷含 collectingAt(Date)', bag.warn[0]?.[0]?.collectingAt instanceof Date);
    check('S4 告警路径未调用 releaseLock', rel.length === 0, `got=${rel.length}`);
    check('S4 doc.collectStatus 未被改动', doc.collectStatus === 'collecting', `got=${doc.collectStatus}`);
}

// S5: collectingAt 在 4h 内 -> 无 warn（防误报）
{
    const doc = { _id: 'S5', chain: 'eth', address: '0xS5', deviceId: 'd5', collectStatus: 'collecting', collectOwner: '7', collectingAt: new Date(NOW - 1 * HOUR) };
    const rel = []; const bag = mkLogger();
    const warned = await m.warnStaleCollecting([doc], { logger: loggerSink(bag), now: NOW });
    line(`S5 out: ${JSON.stringify({ warned, releaseCalls: rel.length, warns: bag.warn.length })}`);
    check('S5 无 warn', bag.warn.length === 0, `got=${bag.warn.length}`);
    check('S5 warned===0', warned === 0);
}

// ---------------------------------------------------------------------------
// schema 增量断言（真实 derived-address.js 副本经 mongoose 桩）
// ---------------------------------------------------------------------------
line('--- schema 增量 ---');
{
    const schema = da?.DerivedAddress?.__schema;
    check('derived-address: 存在 __schema', !!schema);
    const co = schema?.obj?.collectOwner;
    check('derived-address: 新增字段 collectOwner(String, default \'\')',
        !!co && co.type === String && co.default === '', `got=${JSON.stringify(co)}`);
    const ca = schema?.obj?.collectingAt;
    check('derived-address: 新增字段 collectingAt(Date)', !!ca && ca.type === Date, `got=${JSON.stringify(ca)}`);
    const idx = (schema?._indexes || []).some((i) => i.spec && i.spec.collectStatus === 1 && i.spec.collectingAt === 1);
    check('derived-address: 新增索引 {collectStatus:1, collectingAt:1}', idx);
    const st = schema?.obj?.collectStatus;
    check('derived-address: 既有 collectStatus 语义未变（enum 6 值）',
        !!st && Array.isArray(st.enum) && st.enum.length === 6 && st.default === 'idle');
}

line('-------------------------------------');
line(`RESULT: passed=${passed} failed=${failed}`);
if (failed > 0) {
    line('GREEN? NO（存在失败断言）');
    process.exit(1);
}
line('GREEN: all assertions passed');
process.exit(0);
