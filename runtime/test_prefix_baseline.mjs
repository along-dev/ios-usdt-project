/**
 * 对**修正前**的 chain-router.js（备份副本）跑同一套断言，
 * 用于量化"原 87 断言中，有多少是真断言、有多少断言了错误结论"。
 *
 * 运行：
 *   E:\CTF\runtime\node\node.exe _integration\_fix_work\test_prefix_baseline.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const BK = process.argv[2];
if (!BK) { console.error('用法: node test_prefix_baseline.mjs <备份chain-router.js路径>'); process.exit(2); }

const mod = await import(pathToFileURL(BK).href);

let pass = 0, fail = 0;
const failures = [];
function ok(c, l, d) { if (c) pass++; else { fail++; failures.push(l + (d ? ' :: ' + d : '')); } }
function eq(a, b, l) { ok(a === b, l, `expected=${JSON.stringify(b)} actual=${JSON.stringify(a)}`); }

const {
  CHAINS, DARKSWORD_VERSION_BUILDS, SBX0_COVERED_BUILDS,
  darkswordStageReach, pickChain,
} = mod;

// —— 与修正后同一组"真值"断言（真值来自源文件实测）——
eq(DARKSWORD_VERSION_BUILDS['18,4'], '22E240', '版本键18,4 -> 22E240');
eq(DARKSWORD_VERSION_BUILDS['18,4,1'], '22E252', '版本键18,4,1 -> 22E252');
eq(DARKSWORD_VERSION_BUILDS['18,5'], '22F76', '版本键18,5 -> 22F76');
eq(DARKSWORD_VERSION_BUILDS['18,6'], '22G86', '版本键18,6 -> 22G86');
eq(DARKSWORD_VERSION_BUILDS['18,6,1'], '22G90', '版本键18,6,1 -> 22G90');
eq(DARKSWORD_VERSION_BUILDS['18,6,2'], '22G100', '版本键18,6,2 -> 22G100');

eq(CHAINS.coruna.min.join('.'), '15.2.0', 'coruna.min = 15.2.0');
eq(CHAINS.coruna.max.join('.'), '17.2.1', 'coruna.max = 17.2.1');
eq(CHAINS.coruna.iphoneOnly, true, 'coruna.iphoneOnly = true');
eq(CHAINS.darksword.min.join('.'), '18.4.0', 'darksword.min = 18.4.0');
eq(CHAINS.darksword.max.join('.'), '18.6.2', 'darksword.max = 18.6.2');

// —— 这几条是原型"断言了错误结论"的部分 ——
eq(SBX0_COVERED_BUILDS.length, 6, '[真值] SBX0_COVERED_BUILDS 应为 6 个 build');
eq(darkswordStageReach([18, 5, 0]).reach, 'full', '[真值] 18.5 应 full');
eq(darkswordStageReach([18, 6, 0]).reach, 'full', '[真值] 18.6 应 full');
eq(darkswordStageReach([18, 6, 1]).reach, 'full', '[真值] 18.6.1 应 full');
eq(darkswordStageReach([18, 6, 2]).reach, 'full', '[真值] 18.6.2 应 full');
ok(!('partialFrom' in CHAINS.darksword), '[真值] 不应存在 partialFrom');

const ua5 = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X)';
eq(pickChain(ua5).partial, false, '[真值] iOS 18.5 partial 应为 false');

// —— 版本无关的纯逻辑断言（修正前后都应为真）——
eq(pickChain('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)').chain, 'coruna', '17.0 -> coruna');
eq(pickChain('Mozilla/5.0 (iPad; CPU OS 18_5 like Mac OS X)'), null, 'iPad -> null');
eq(pickChain('Mozilla/5.0 (iPhone; CPU iPhone OS 18_3 like Mac OS X)'), null, '18.3 -> null');
eq(pickChain('Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X)'), null, '18.7 -> null');
eq(pickChain('Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X)'), null, '17.3 -> null');

console.log(`修正前原型 vs 真值断言: 通过 ${pass} / 失败 ${fail}`);
console.log('--- 修正前原型断言错误的条目 ---');
for (const f of failures) console.log('  ✗ ' + f);
