// 全量交叉表：对 174 个 app_dist_* 同时给出 manifest / 扁平件 / HEAD / 工作树 四个值的关系
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';

const REPO = 'E:\\USDT项目';
const S = '02-backend-node/src_restored';
const F = '02-backend-node/src';
const sh = (b) => createHash('sha256').update(b).digest('hex');

const walk = (d, b = d, o = []) => {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, e.name);
    e.isDirectory() ? walk(p, b, o) : (e.name.endsWith('.js') && o.push(path.relative(b, p).split(path.sep).join('/')));
  }
  return o;
};
const map = new Map(walk(path.join(REPO, S)).map((r) => ['app_dist_' + r.replace(/\//g, '_'), r]));

// manifest
const ents = [];
for (const l of fs.readFileSync(path.join(REPO, '_manifest.sha256'), 'utf8').split(/\r?\n/)) {
  const m = l.match(/^([0-9A-Fa-f]{64})\s+\*?(.+)$/);
  if (m && m[2].trim().startsWith('app_dist_')) ents.push({ man: m[1].toLowerCase(), f: m[2].trim() });
}

const headSha = (rel) => { try { return sh(execFileSync('git', ['show', `HEAD:${S}/${rel}`], { cwd: REPO, maxBuffer: 1 << 28 })); } catch { return null; } };
// 整批 git cat-file 太慢，改用一次 ls-tree+cat 也行；这里按需单取（174 次可接受）

let n = { flatEqHead: 0, flatNeHead: 0, flatOnly: 0, manEqFlat: 0, manEqHead: 0, manEqNeither: 0 };
const rows = [];
for (const e of ents) {
  const rel = map.get(e.f);
  const flatP = path.join(REPO, F, e.f);
  const flat = fs.existsSync(flatP) ? sh(fs.readFileSync(flatP)) : null;
  const wt = fs.existsSync(path.join(REPO, S, rel)) ? sh(fs.readFileSync(path.join(REPO, S, rel))) : null;
  const hd = headSha(rel);
  const isFlatEqHead = flat === hd;
  isFlatEqHead ? n.flatEqHead++ : n.flatNeHead++;
  if (e.man === flat) n.manEqFlat++;
  if (e.man === hd) n.manEqHead++;
  if (e.man !== flat && e.man !== hd) n.manEqNeither++;
  rows.push({ f: e.f, rel, man: e.man, flat, hd, wt, isFlatEqHead });
}

console.log('条数 =', ents.length);
console.log('flat == HEAD(src_restored@HEAD)  =', n.flatEqHead);
console.log('★ flat != HEAD（即：扁平件落后于已提交的源）=', n.flatNeHead);
console.log('manifest == flat                 =', n.manEqFlat);
console.log('manifest == HEAD                 =', n.manEqHead);
console.log('manifest 与两者都不同            =', n.manEqNeither);
console.log('\n=== flat != HEAD 的逐件（这才是【既有分叉】的完整清单）===');
for (const r of rows.filter((x) => !x.isFlatEqHead)) {
  console.log(`  ${r.f}`);
  console.log(`      flat=${String(r.flat).slice(0, 12)}  HEAD=${String(r.hd).slice(0, 12)}  manifest=${r.man.slice(0, 12)}  ← src_restored/${r.rel}`);
}
