/**
 * I1-C2 运行时实测（B 路替代方案）：串起【真实模块链】验证 entries 非空。
 *
 * ★ 为什么不是完整 HTTP e2e：本机无 MongoDB(27018)/Redis(16379)/docker（实测），
 *   无法起真实服务。故改为【真实模块 + 最小 mock】驱动同一条代码路径：
 *     syncCorunaPayloads/syncDarkswordPayloads  →  （模拟落库）→ moduleBelongsToChain 过滤 → entries
 *   这比纯静态断言强：它真的跑了 packModule（7z 加密）与分链过滤。
 *
 * ★ 未覆盖部分显式声明（V0 D-4）。
 */
import path from 'node:path';
import fs from 'node:fs';

const ROOT = 'E:\\USDT项目';
const C2 = path.join(ROOT, '02-backend-node', 'src_restored', 'plugins', 'c2', 'services');
const TPL = path.join(ROOT, '02-backend-node', 'templates');

const results = [];
function rec(name, ok, detail) {
  results.push({ name, ok, detail });
  console.log(`  [${ok ? 'PASS' : 'FAIL'}] ${name}: ${detail}`);
}

console.log('=== I1-C2 运行时实测（真实模块链，B 路）===');
console.log('');

const coruna = await import('file:///' + path.join(C2, 'chain-coruna.js').replace(/\\/g, '/'));
const dark = await import('file:///' + path.join(C2, 'chain-darksword.js').replace(/\\/g, '/'));
const router = await import('file:///' + path.join(C2, 'chain-router.js').replace(/\\/g, '/'));

// T1: coruna 同步真实产出 15 条 records（含真实 7z 加密）
let corunaRecs = [];
{
  const DSH_TMP = (process.env.DSH_VERIFY_TMP || '').trim();
const RT_STORAGE = DSH_TMP ? path.join(DSH_TMP, '.rt_storage')
                           : path.join(ROOT, '02-backend-node', '.rt_storage');
// ── 原行（留痕）：… path.join(ROOT, '02-backend-node', '.rt_storage') …
const r = await coruna.syncCorunaPayloads(path.join(TPL, 'coruna'), RT_STORAGE, true, 'auto');
  corunaRecs = r.records;
  const errs = r.report.filter((x) => x.error);
  rec('T1 syncCorunaPayloads 真实产出', corunaRecs.length === 15 && errs.length === 0,
      `records=${corunaRecs.length} errs=${errs.length}`);
}

// T2: darksword 同步真实产出 5 条
let darkRecs = [];
{
  // ★ T26 收尾（E-03）：同 T1 —— 可被 DSH_VERIFY_TMP 覆盖
  const _t = (process.env.DSH_VERIFY_TMP || '').trim();
  const RT2 = _t ? path.join(_t, '.rt_storage') : path.join(ROOT, '02-backend-node', '.rt_storage');
  // ── 原行（留痕）：… path.join(ROOT, '02-backend-node', '.rt_storage') …
  const r = await dark.syncDarkswordPayloads(path.join(TPL, 'darksword'), RT2, 'http://localhost:3000', false, null, 'auto');
  darkRecs = r.records;
  const errs = r.report.filter((x) => x.error);
  rec('T2 syncDarkswordPayloads 真实产出', darkRecs.length === 5 && errs.length === 0,
      `records=${darkRecs.length} errs=${errs.length}`);
}

// T3: ★ 核心 —— 落库后过 moduleBelongsToChain 过滤，entries 必须非空且项数正确
{
  const all = [...corunaRecs, ...darkRecs];   // 模拟 Payload 集合
  const corunaEntries = all.filter((m) => router.moduleBelongsToChain(m.name, 'coruna'));
  const darkEntries = all.filter((m) => router.moduleBelongsToChain(m.name, 'darksword'));
  rec('T3 coruna 链过滤 entries 非空', corunaEntries.length === 15, `entries=${corunaEntries.length}`);
  rec('T3 darksword 链过滤 entries 非空', darkEntries.length === 5, `entries=${darkEntries.length}`);
}

// T4: 红态对照 —— 仅 templates/payloads 的 dylib（原唯一来源）过链过滤必须为 0
{
  const dylibs = fs.readdirSync(path.join(TPL, 'payloads')).filter((f) => f.endsWith('.dylib'))
    .map((f) => path.basename(f, '.dylib')).filter((n) => n !== 'corepayload' && n !== 'loader');
  const hit = dylibs.filter((n) => router.moduleBelongsToChain(n, 'coruna') || router.moduleBelongsToChain(n, 'darksword'));
  rec('T4 红态对照：12 个 dylib 过链过滤 = 0', hit.length === 0, `dylib 数=${dylibs.length} 命中=${hit.length}`);
}

// T5: 落库 records 的形状必须满足 config-builder 的 entries 字段契约
{
  const sample = corunaRecs[0];
  const need = ['name', 'sha256', 'size', 'encryptedPath', 'packMode'];
  const miss = need.filter((k) => sample[k] === undefined || sample[k] === null || sample[k] === '');
  rec('T5 records 字段完整（供 entries 下发）', miss.length === 0, `缺=${miss.join(',') || '无'}`);
}

// T6: 加密产物确实落盘（证明 packModule 真跑了，非空壳）
{
  // ★ T26 收尾（E-03）：同 T1/T2 —— 可被 DSH_VERIFY_TMP 覆盖
  const _t = (process.env.DSH_VERIFY_TMP || '').trim();
  // ── 原行（留痕）：const p = path.join(ROOT, '02-backend-node', '.rt_storage');
  const p = _t ? path.join(_t, '.rt_storage') : path.join(ROOT, '02-backend-node', '.rt_storage');
  const files = fs.existsSync(p) ? fs.readdirSync(p, { recursive: true }).filter((f) => String(f).endsWith('.dat')) : [];
  rec('T6 加密 .dat 文件实际落盘', files.length >= 15, `落盘 .dat 数=${files.length}`);
}

console.log('');
const fails = results.filter((r) => !r.ok);
console.log(`=== ${results.length - fails.length}/${results.length} 通过 ===`);
console.log('');
console.log('★ 覆盖声明：');
console.log('  - 已覆盖：真实 packModule(7z) 加密、records 字段形状、分链过滤、entries 非空与项数。');
console.log('  - 未覆盖（V0 D-4）：真实 MongoDB 落库、Redis、HTTP 端到端、真机投递。');
console.log('    ⇒ 本机无 mongod/redis/docker（实测端口 27018/16379 均不可达），故上述【未覆盖】。');

if (fails.length) { console.log(`RESULT=RED  ${fails.length} 项失败`); process.exit(1); }
console.log('RESULT=GREEN');
