/**
 * I1-C2 补充判据：darksword entries 实际项数（契约 C-3 要求恰 5）。
 * 用法：node verify_i1c2_darksword_entries.mjs
 */
import path from 'node:path';
import fs from 'node:fs';

const ROOT = 'E:\\USDT项目';
const C2 = path.join(ROOT, '02-backend-node', 'src_restored', 'plugins', 'c2', 'services');
const DS_DIR = path.join(ROOT, '02-backend-node', 'templates', 'darksword');
const EXPECT = 5;
const DSH_TMP = (process.env.DSH_VERIFY_TMP || '').trim();
// ★ T26 收尾（E-03）：可被 DSH_VERIFY_TMP 覆盖；不设则保持原路径
// ── 原行（留痕）：const STORAGE = path.join(ROOT, '02-backend-node', '.verify_tmp_storage_ds');
const STORAGE = DSH_TMP ? path.join(DSH_TMP, '.verify_tmp_storage_ds')
                        : path.join(ROOT, '02-backend-node', '.verify_tmp_storage_ds');

console.log('=== darksword entries 实测（契约 C-3：恰 5）===');
if (!fs.existsSync(DS_DIR)) {
  console.log(`  [FAIL] 副本目录不存在: ${DS_DIR}`);
  process.exit(1);
}

const mod = await import('file:///' + path.join(C2, 'chain-darksword.js').replace(/\\/g, '/'));
// ★ include186 = false：契约 C-3 冻结 darksword 恰 5 项（= DARKSWORD_MODULES 本身）
const { records, report } = await mod.syncDarkswordPayloads(
  DS_DIR, STORAGE, 'http://localhost:3000', false, null, 'auto'
);

console.log(`  darksword entries 实际 = ${records.length}（契约须 ${EXPECT}）`);
console.log('  逐项清单:');
for (const r of records) console.log(`    - ${r.name}`);

const errs = report.filter((r) => r.error);
if (errs.length) {
  console.log(`  [FAIL] 有 ${errs.length} 个文件处理失败:`, errs);
}

// 契约 C-3 的 5 项名
const EXPECT_NAMES = ['ds_rce_loader', 'ds_rce_worker', 'ds_sbx0', 'ds_sbx1', 'ds_pe_main'];
const got = records.map((r) => r.name);
const missing = EXPECT_NAMES.filter((n) => !got.includes(n));

let ok = true;
if (records.length !== EXPECT) { console.log(`  [FAIL] 项数不符`); ok = false; }
if (missing.length) { console.log(`  [FAIL] 缺: ${missing.join(', ')}`); ok = false; }
if (errs.length) ok = false;
// 负例：不含 tglib
if (got.some((n) => n.includes('tglib'))) { console.log('  [FAIL] 含 tglib'); ok = false; }

if (ok) { console.log('RESULT=GREEN  darksword entries 恰 5 且名正确'); process.exit(0); }
console.log('RESULT=RED');
process.exit(1);
