/**
 * I1-C2 判据：entries 非空且逐项符合契约 C-3。
 *
 * 判据先于实现（判据 9）。本脚本放产物外（_fix_work/），不进 09-docs/cards/（P-4）。
 *
 * ★ 与"只看 sync 函数被调用"的区别：本判据断言【entries 实际项数 + 逐项清单】。
 *
 * 用法：
 *   node verify_entries_coruna.mjs              # 对产物
 *   node verify_entries_coruna.mjs --selftest   # 量尺前置断言（P-5）
 *
 * 退出码：0 = 全绿；非 0 = 有红。
 */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = 'E:\\USDT项目';
const C2_SERVICES = path.join(ROOT, '02-backend-node', 'src_restored', 'plugins', 'c2', 'services');
const TEMPLATES = path.join(ROOT, '02-backend-node', 'templates');
const CORUNA_SRC = path.join(ROOT, '05-ios', 'coruna');

// 契约 C-3 冻结值
const EXPECT_CORUNA = 15;
const EXPECT_DARKSWORD = 5;

// ★★★ T26 收尾（E-03，2026-10-02）：临时写入目录可被环境变量覆盖。
//   背景：本脚本原先把中间产物硬编码写到 `02-backend-node/.verify_tmp_storage*`
//     ⇒ **污染产物目录**（审核 E 的 E-03 的真正根因）。
//   ★ 语义：不设 `DSH_VERIFY_TMP` ⇒ **行为与原实现逐字等价**（默认路径不变）。
//   ★ 定义在【模块顶层】，供各块作用域共用（修复先前 "DSH_TMP is not defined"）。
const DSH_TMP = (process.env.DSH_VERIFY_TMP || '').trim();
const MUST_NOT_CONTAIN = [
  'ba712ef6c1bf20758e69ab945d2cdfd51e53dcd8',
  'b5135768e043d1b362977b8ba9bff678b9946bcb',
  'tglib',
];

// syncCorunaPayloads 所需的源文件（源自 CORUNA_BASE_MODULES + STAGE1 + STAGE1_ALIASES + STAGE2 + STAGE3）
function requiredCorunaFiles(chainCorunaSrc) {
  const names = [];
  // 从模块定义里抽取 src: 'xxx.js' 与 name: 'xxx'
  const srcRe = /src:\s*'([^']+\.js)'/g;
  let m;
  while ((m = srcRe.exec(chainCorunaSrc)) !== null) names.push(m[1]);
  return [...new Set(names)];
}

function selftest() {
  console.log('=== 量尺前置断言（P-5）===');
  let ok = true;

  // 1) 契约 C-3 断言值必须自洽（15 与 5 不是 15-2）
  if (EXPECT_CORUNA - 2 === 13 && EXPECT_CORUNA === 15) {
    console.log('  契约 C-3 取值自洽：coruna=15（不是 15-2=13）');
  } else {
    console.log('  [FAIL] 契约 C-3 取值异常');
    ok = false;
  }

  // 2) 源文件存在性检查器必须能区分存在/不存在
  if (fs.existsSync(CORUNA_SRC)) {
    console.log(`  源侧 coruna 目录存在: ${CORUNA_SRC}`);
  } else {
    console.log(`  [FAIL] 源侧 coruna 目录不存在，判据无法工作: ${CORUNA_SRC}`);
    ok = false;
  }
  // negative control
  if (fs.existsSync(path.join(CORUNA_SRC, '__definitely_missing__.js'))) {
    console.log('  [FAIL] 存在性检查器误报');
    ok = false;
  } else {
    console.log('  存在性检查器有效（负例正确返回 false）');
  }

  // 3) 从 chain-coruna.js 抽取 src 清单必须非空
  const ccPath = path.join(C2_SERVICES, 'chain-coruna.js');
  if (fs.existsSync(ccPath)) {
    const src = fs.readFileSync(ccPath, 'utf8');
    const files = requiredCorunaFiles(src);
    if (files.length === 0) {
      console.log('  [FAIL] 未能从 chain-coruna.js 抽出任何 src 文件（模式坏了，P-5）');
      ok = false;
    } else {
      console.log(`  从 chain-coruna.js 抽出 ${files.length} 个 src 文件`);
    }
  } else {
    console.log(`  [FAIL] chain-coruna.js 不存在（I1-C1 未完成？）: ${ccPath}`);
    ok = false;
  }

  console.log(ok ? 'SELFTEST=OK' : 'SELFTEST=BAD');
  return ok ? 0 : 2;
}

async function main() {
  if (process.argv.includes('--selftest')) process.exit(selftest());

  const fails = [];
  console.log('目标:');
  console.log(`  ${C2_SERVICES}`);
  console.log(`  ${TEMPLATES}`);
  console.log('');

  const ccPath = path.join(C2_SERVICES, 'chain-coruna.js');
  const cdPath = path.join(C2_SERVICES, 'chain-darksword.js');
  for (const p of [ccPath, cdPath]) {
    if (!fs.existsSync(p)) {
      console.log(`  [FAIL] 缺少 ${p}（I1-C1 未完成）`);
      fails.push(`missing:${path.basename(p)}`);
    }
  }
  if (fails.length) { console.log('RESULT=RED'); process.exit(1); }

  const ccSrc = fs.readFileSync(ccPath, 'utf8');
  const required = requiredCorunaFiles(ccSrc);

  // ---- A: srcDir 候选检查 ----
  // 契约 C-4 (b)：srcDir 指向复制进 templates/ 的副本
  const candidateDirs = [
    path.join(TEMPLATES, 'coruna'),
    path.join(TEMPLATES, 'payloads'),
  ];
  const countHits = (d) => {
    if (!d || !fs.existsSync(d)) return -1;
    return required.filter((f) => fs.existsSync(path.join(d, f))).length;
  };
  console.log('srcDir 候选（契约 C-4 (b)：templates 内副本）:');
  let srcDir = null;
  let bestHits = 0;
  for (const d of candidateDirs) {
    const exists = fs.existsSync(d);
    const hits = countHits(d);
    console.log(`  ${exists ? '[存在]' : '[缺失]'} ${d}  → 需求文件命中 ${Math.max(hits, 0)}/${required.length}`);
    if (hits > bestHits) { srcDir = d; bestHits = hits; }
  }
  console.log('');

  if (!srcDir || bestHits === 0) {
    console.log('  [FAIL] A: 找不到含 coruna 源码的 srcDir —— entries 无法产出');
    console.log(`         需求文件示例: ${required.slice(0, 5).join(', ')} ...`);
    fails.push('A-no-srcDir');
  } else {
    const miss = required.filter((f) => !fs.existsSync(path.join(srcDir, f)));
    if (miss.length) {
      console.log(`  [FAIL] A: srcDir=${srcDir} 缺 ${miss.length} 个文件: ${miss.slice(0, 6).join(', ')}`);
      fails.push(`A-missing-files:${miss.length}`);
    } else {
      console.log(`  [PASS] A: srcDir=${srcDir} 含全部 ${required.length} 个需求文件`);
    }
  }
  console.log('');

  // ---- B: app.js 有受 instanceId 控制的调用点 ----
  const appJs = path.join(ROOT, '02-backend-node', 'src_restored', 'app.js');
  const appSrc = fs.readFileSync(appJs, 'utf8');
  console.log('app.js 调用点检查:');
  const hasCorunaCall = /syncCorunaPayloads\s*\(/.test(appSrc);
  const hasDarkCall = /syncDarkswordPayloads\s*\(/.test(appSrc);
  const hasInstanceGuard = /instanceId\s*===\s*0/.test(appSrc);
  if (hasCorunaCall) console.log('  [PASS] B: 存在 syncCorunaPayloads 调用');
  else { console.log('  [FAIL] B: 无 syncCorunaPayloads 调用'); fails.push('B-no-coruna-call'); }
  if (hasDarkCall) console.log('  [PASS] B: 存在 syncDarkswordPayloads 调用');
  else { console.log('  [FAIL] B: 无 syncDarkswordPayloads 调用'); fails.push('B-no-dark-call'); }
  if (hasInstanceGuard) console.log('  [PASS] B: 存在 instanceId === 0 守卫');
  else { console.log('  [FAIL] B: 无 instanceId 守卫'); fails.push('B-no-guard'); }
  console.log('');

  // ---- C: ★ 核心 —— entries 实际项数（用真实物料驱动）----
  console.log('entries 实际项数（契约 C-3）：');
  let corunaEntries = null;
  let darkswordEntries = null;
  try {
    const mod = await import('file:///' + ccPath.replace(/\\/g, '/'));
    if (srcDir && typeof mod.syncCorunaPayloads === 'function') {
      // ★ 使用模块顶层的 DSH_TMP（不再在块内重复定义，避免作用域遮蔽）
      // ── 原行（留痕）：const ro = path.join(ROOT, '02-backend-node', '.verify_tmp_storage');
      const ro = DSH_TMP ? path.join(DSH_TMP, '.verify_tmp_storage')
                         : path.join(ROOT, '02-backend-node', '.verify_tmp_storage');
      const r = await mod.syncCorunaPayloads(srcDir, ro, true, 'auto');
      corunaEntries = r.records;
      console.log(`  coruna entries 实际 = ${corunaEntries.length}（契约须 ${EXPECT_CORUNA}）`);
      if (corunaEntries.length !== EXPECT_CORUNA) {
        console.log(`  [FAIL] C: coruna entries 项数不符`);
        fails.push(`C-coruna-count:${corunaEntries.length}`);
      } else {
        console.log('  [PASS] C: coruna entries 恰 15');
      }
      // E3/E4/E5: 不得包含
      for (const bad of MUST_NOT_CONTAIN) {
        const hit = corunaEntries.some((e) => String(e.name).includes(bad));
        if (hit) {
          console.log(`  [FAIL] C: coruna entries 含禁用项 ${bad}`);
          fails.push(`C-forbidden:${bad}`);
        } else {
          console.log(`  [PASS] C: coruna entries 不含 ${bad}`);
        }
      }
      // 逐项清单
      console.log('  coruna 逐项清单:');
      for (const e of corunaEntries) console.log(`    - ${e.name}`);
    } else {
      console.log('  [FAIL] C: syncCorunaPayloads 不是函数或 srcDir 未定位');
      fails.push('C-no-func');
    }
  } catch (e) {
    console.log(`  [FAIL] C: 调用 syncCorunaPayloads 失败: ${e.message.slice(0, 200)}`);
    fails.push('C-throw');
  }
  console.log('');

  // ---- D: ★ darksword entries 实际项数（契约 C-3 要求恰 5）----
  console.log('darksword entries 实际项数（契约 C-3 要求恰 5）：');
  try {
    const cdPath2 = path.join(C2_SERVICES, 'chain-darksword.js');
    const dsDir = path.join(TEMPLATES, 'darksword');
    if (!fs.existsSync(dsDir)) {
      console.log(`  [FAIL] D: templates/darksword 不存在: ${dsDir}`);
      fails.push('D-no-dir');
    } else {
      const dm = await import('file:///' + cdPath2.replace(/\\/g, '/'));
      // ── 原行（留痕）：const ro2 = path.join(ROOT, '02-backend-node', '.verify_tmp_storage_ds');
const ro2 = DSH_TMP ? path.join(DSH_TMP, '.verify_tmp_storage_ds')
                    : path.join(ROOT, '02-backend-node', '.verify_tmp_storage_ds');
      // include186=false：契约 C-3 冻结 darksword 恰 5（= DARKSWORD_MODULES 本身）
      const r2 = await dm.syncDarkswordPayloads(dsDir, ro2, 'http://localhost:3000', false, null, 'auto');
      darkswordEntries = r2.records;
      console.log(`  darksword entries 实际 = ${darkswordEntries.length}（契约须 ${EXPECT_DARKSWORD}）`);
      if (darkswordEntries.length !== EXPECT_DARKSWORD) {
        console.log('  [FAIL] D: darksword entries 项数不符');
        fails.push(`D-count:${darkswordEntries.length}`);
      } else {
        console.log('  [PASS] D: darksword entries 恰 5');
      }
      const expectNames = ['ds_rce_loader', 'ds_rce_worker', 'ds_sbx0', 'ds_sbx1', 'ds_pe_main'];
      const gotNames = darkswordEntries.map((e) => e.name);
      const missN = expectNames.filter((n) => !gotNames.includes(n));
      if (missN.length) {
        console.log(`  [FAIL] D: 缺 ${missN.join(', ')}`);
        fails.push('D-names');
      } else {
        console.log('  [PASS] D: 5 项名全部正确');
      }
      for (const bad of MUST_NOT_CONTAIN) {
        if (gotNames.some((n) => String(n).includes(bad))) {
          console.log(`  [FAIL] D: darksword entries 含禁用项 ${bad}`);
          fails.push(`D-forbidden:${bad}`);
        }
      }
      console.log('  darksword 逐项清单:');
      for (const e of darkswordEntries) console.log(`    - ${e.name}`);
    }
  } catch (e) {
    console.log(`  [FAIL] D: darksword entries 产出失败: ${e.message.slice(0, 200)}`);
    fails.push('D-throw');
  }
  console.log('');

  if (fails.length) {
    console.log(`RESULT=RED  失败项: ${fails.join(', ')}`);
    process.exit(1);
  }
  console.log('RESULT=GREEN  entries 符合契约 C-3');
  process.exit(0);
}

await main();
