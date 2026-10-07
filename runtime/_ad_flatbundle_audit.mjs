// 扁平副本分叉取证：src/app_dist_*.js 与 src_restored/** 逐件比对
// 命名规律（据 09-docs/ledger/L009-manifest重算台账.md:60）：
//   app_dist_<相对路径，目录分隔符替换为 _>.js  ←  src_restored/<相对路径>.js
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';

const ROOT = 'E:\\USDT项目\\02-backend-node';
const SRC_RESTORED = path.join(ROOT, 'src_restored');
const FLAT = path.join(ROOT, 'src');

function walk(dir, base = dir, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, base, out);
    else if (e.name.endsWith('.js')) out.push(path.relative(base, p).split(path.sep).join('/'));
  }
  return out;
}
const sha = (f) => createHash('sha256').update(fs.readFileSync(f)).digest('hex');
const flatName = (rel) => 'app_dist_' + rel.replace(/\//g, '_');

// 1) 期望映射：src_restored/** -> 扁平名
const restored = walk(SRC_RESTORED);
const expect = new Map();          // 扁平名 -> src_restored 相对路径
const collisions = [];
for (const rel of restored) {
  const n = flatName(rel);
  if (expect.has(n)) collisions.push([n, expect.get(n), rel]);
  else expect.set(n, rel);
}

// 2) 实际扁平件
const actual = fs.readdirSync(FLAT).filter((f) => f.startsWith('app_dist_') && f.endsWith('.js'));

// 3) 比对
const identical = [], divergent = [], orphanFlat = [], missingFlat = [];
for (const f of actual) {
  const rel = expect.get(f);
  if (!rel) { orphanFlat.push(f); continue; }
  const a = path.join(FLAT, f), b = path.join(SRC_RESTORED, rel);
  const sa = sha(a), sb = sha(b);
  if (sa === sb) identical.push(f);
  else divergent.push({ flat: f, restored: rel, flatBytes: fs.statSync(a).size, restoredBytes: fs.statSync(b).size, flatSha: sa, restoredSha: sb });
}
const actualSet = new Set(actual);
for (const [n, rel] of expect) if (!actualSet.has(n)) missingFlat.push(rel);
// 也检查 src/ 里非 app_dist_* 的 js
const otherFlat = fs.readdirSync(FLAT).filter((f) => f.endsWith('.js') && !f.startsWith('app_dist_'));

console.log('=== 计数 ===');
console.log('src_restored/*.js      =', restored.length);
console.log('src/app_dist_*.js      =', actual.length);
console.log('src/ 其它 .js          =', otherFlat.length, otherFlat.slice(0, 5));
console.log('扁平名冲突（两个源映到同一名） =', collisions.length);
for (const c of collisions) console.log('   ⚠️', c[0], '←', c[1], '/', c[2]);
console.log('逐件一致               =', identical.length);
console.log('★ 实质分叉             =', divergent.length);
console.log('孤儿扁平件（无源可对） =', orphanFlat.length, orphanFlat);
console.log('缺失扁平件（有源无产物）=', missingFlat.length);

console.log('\n=== ★ 分叉清单（逐件）===');
divergent.sort((x, y) => y.flatBytes - x.flatBytes);
for (const d of divergent) {
  console.log(`  ${d.flat}`);
  console.log(`      ← src_restored/${d.restored}`);
  console.log(`      flat=${d.flatBytes}B/${d.flatSha.slice(0, 12)}  restored=${d.restoredBytes}B/${d.restoredSha.slice(0, 12)}  Δbytes=${d.flatBytes - d.restoredBytes}`);
}
if (missingFlat.length) {
  console.log('\n=== 缺失扁平件（有源、无产物）===');
  for (const m of missingFlat) console.log('  ', m);
}
