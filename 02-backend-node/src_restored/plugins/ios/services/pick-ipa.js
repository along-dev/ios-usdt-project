/**
 * pickIpa(ua) —— IPA 分发件判决器（卡 T120 · IPA-2）
 *
 * ★ 定位：把「iOS 设备版本」映射为「该投哪一代 FilzaSlop 基座」。
 *   这是 IPA 显式投递链的**版本轴**，与网页链（coruna/darksword）无关。
 *
 * ★ 独立于 chain-router（⛔ 不 import、不耦合）：
 *   chain-router.pickChain 管的是【网页链】（能否造出注入前提，轴 A）；
 *   本模块管的是【IPA 代际】（注入后拿到什么能力，轴 B）。
 *   两者正交，不得互相替代（依据 W-IOS-PKG1 §4.1 / IPA方案说明 §三）。
 *
 * ★ 基座两代（IPA方案说明 §二 / W-IOS-PKG1 §4.2 指纹实测）：
 *   - 第 1/2 代（gen12，含链 kexploit_opa334）：门禁 17.0 – 26.0.x（硬 exit(1)）
 *   - 第 3 代（gen3，无链，走 MCM/MHA）：无门禁（dlsym 探测）
 *
 * ★ 分发映射（承 Owner 裁决「两代都做、覆盖优先」+ IPA方案说明 §四）：
 *   | iOS 区间         | 代际   | 理由 |
 *   |------------------|--------|------|
 *   | 15.2 – 16.x      | gen3   | 第 1/2 代门禁 17.0 起，16.x 被拒 |
 *   | 17.0 – 17.2.1    | gen12  | coruna ✅ + 门禁内 ✅（能力最全）|
 *   | 17.3 – 18.3.9    | 空档   | 网页链空档（已裁接受）；对照区间 |
 *   | 18.4 – 18.6.2    | gen12  | darksword ✅ + 门禁内 ✅ |
 *   | 18.7+            | gen3   | 无链（第 1/2 代也行但无链可喂）|
 *
 * ★ 已知歧义（如实登记，不静默裁决）：
 *   (1) 17.3 – 18.3.9：Owner 裁决未把此区间指派给任一代；W-IOS-PKG1 §5.3
 *       载「对 17.3–18.3.9 返回 unsupported（不得回退）」⇒ 本模块回 unsupported。
 *   (2) 18.4.2 – 18.6.2：Owner 裁决只显式写「18.4–18.4.1」，但 darksword 网页链
 *       实际覆盖 18.4–18.6.2，且第 1/2 代门禁 17.0–26.0.x 含之 ⇒ 本模块按
 *       【基座门禁 + darksword 全区间】扩展归 gen12，并在 note 中标注待 Owner 确认。
 */

export const GENERATIONS = Object.freeze({
  GEN12: 'gen12', // 第 1/2 代（含内核链 kexploit_opa334）
  GEN3: 'gen3',   // 第 3 代（无链，MCM/MHA）
});

// 第 1/2 代门禁区间（含端点，硬 exit(1) 之外）
const GEN12_GATE_MIN = [17, 0, 0];
const GEN12_GATE_MAX = [26, 0, 0];

// 分发映射区间端点
const RANGE_GEN3_LOW = [15, 2, 0];   // gen3 下界（coruna 最低偏移表）
const RANGE_GEN12_CORUNA_MAX = [17, 2, 1];
const RANGE_GAP_MAX = [18, 3, 9];    // 网页链空档上界
const RANGE_GEN12_DARKSWORD_MAX = [18, 6, 2];

/** 三段版本号比较，缺失段按 0 处理。 */
export function cmp3(a, b) {
  const n = Math.max(a.length, b.length);
  for (let i = 0; i < n; i++) {
    const x = a[i] || 0;
    const y = b[i] || 0;
    if (x !== y) return x < y ? -1 : 1;
  }
  return 0;
}

/** 从 UA 解析 iOS 版本，如 "iPhone OS 18_5" -> [18,5,0]；非 iOS 返回 null。 */
export function parseIosVersion(ua) {
  if (!ua) return null;
  const m = /iPhone OS (\d+)[._](\d+)(?:[._](\d+))?/i.exec(ua);
  if (!m) return null;
  return [Number(m[1]), Number(m[2]), Number(m[3] || 0)];
}

/** 是否 iPhone（两条链 + 基座均仅 iPhone；iPad/iPod 无偏移）。 */
export function isIphone(ua) {
  return /iPhone/.test(ua || '');
}

/** 版本数组 → "x.y.z" 字符串（供展示/诊断）。 */
export function versionString(v) {
  return (v || []).join('.');
}

/**
 * ★ 核心：把设备 iOS 版本映射为应投的代际。
 *
 * @param {string} ua navigator.userAgent（或 `?ua=` 显式传入）
 * @returns {{
 *   supported: boolean,
 *   version: number[]|null,
 *   generation: 'gen12'|'gen3'|null,
 *   needsKernel: boolean|null,
 *   range: string|null,
 *   note: string,
 *   reason: string
 * }}
 *   supported=false 表示不支持（调用方应回 unsupported，不得回退到默认代）。
 */
export function pickIpa(ua) {
  const unsupported = (reason) => ({
    supported: false,
    version: null,
    generation: null,
    needsKernel: null,
    range: null,
    note: reason,
    reason,
  });

  if (!isIphone(ua)) return unsupported('非 iPhone 设备（仅 iPhone 支持）');
  const v = parseIosVersion(ua);
  if (!v) return unsupported('iOS 版本解析失败');

  // 下界：15.2（coruna 最低偏移表；低于此无载荷可喂）
  if (cmp3(v, RANGE_GEN3_LOW) < 0) {
    return unsupported(`iOS ${versionString(v)} 低于 15.2（载荷无偏移表）`);
  }

  // 15.2 – 16.x → gen3（第 1/2 代门禁 17.0 起，16.x 被硬 exit(1) 拒）
  if (cmp3(v, GEN12_GATE_MIN) < 0) {
    return {
      supported: true, version: v, generation: GENERATIONS.GEN3, needsKernel: false,
      range: '15.2–16.x',
      note: '第 1/2 代门禁 17.0 起，此区间被拒 ⇒ 第 3 代（无链）',
      reason: '',
    };
  }

  // 17.0 – 17.2.1 → gen12（coruna ✅ + 门禁内 ✅，能力最全）
  if (cmp3(v, RANGE_GEN12_CORUNA_MAX) <= 0) {
    return {
      supported: true, version: v, generation: GENERATIONS.GEN12, needsKernel: true,
      range: '17.0–17.2.1',
      note: 'coruna 网页链 ✅ + 第 1/2 代门禁内 ✅（能力最全）',
      reason: '',
    };
  }

  // 17.3 – 18.3.9 → 空档（网页链空档，已裁接受；裁决未指派 ⇒ unsupported，不回退）
  if (cmp3(v, RANGE_GAP_MAX) <= 0) {
    return unsupported(
      `iOS ${versionString(v)} 落在网页链覆盖空档 17.3–18.3.9（裁决未指派任一代，不回退）`
    );
  }

  // 18.4 – 18.6.2 → gen12（darksword ✅ + 门禁内 ✅）
  if (cmp3(v, RANGE_GEN12_DARKSWORD_MAX) <= 0) {
    const beyondExplicit = cmp3(v, [18, 4, 1]) > 0;
    return {
      supported: true, version: v, generation: GENERATIONS.GEN12, needsKernel: true,
      range: '18.4–18.6.2',
      note: beyondExplicit
        ? '★ Owner 裁决只显式列「18.4–18.4.1」；18.4.2–18.6.2 按【基座门禁 17.0–26.0.x + darksword 18.4–18.6.2】扩展归第 1/2 代，待 Owner 确认'
        : 'darksword 网页链 ✅ + 第 1/2 代门禁内 ✅',
      reason: '',
    };
  }

  // 18.7+ → gen3（无链可喂；第 1/2 代虽门禁内，但无链 ⇒ 第 3 代）
  return {
    supported: true, version: v, generation: GENERATIONS.GEN3, needsKernel: false,
    range: '18.7+',
    note: '无网页链可喂（darksword 上界 18.6.2）⇒ 第 3 代（无链）',
    reason: '',
  };
}

/**
 * ★ 从 IPA 文件名解析其【自身】版本号（用于 list 的 version 元数据）。
 * 兼容 `FilzaSlop-v1.0.3-unsigned.ipa` / `FilzaEscaped_DS_1.2` / `FilzaJailed_2.1`。
 * @returns {number[]|null} 解析失败返回 null（如实，不编造）。
 */
export function versionFromFilename(name) {
  const n = String(name || '');
  // 优先匹配 `v1.0.3`（含 `-unsigned` 后缀的文件名）
  let m = /[vV]?(\d+)\.(\d+)(?:\.(\d+))?/.exec(n);
  if (!m) return null;
  return [Number(m[1]), Number(m[2]), Number(m[3] || 0)];
}

/**
 * ★ 从 IPA 文件名分类其【自身】代际（依据 W-IOS-PKG1 §4.2 指纹表，文件名侧推断）。
 *
 * 规则（静态指纹表的事实，非运行时实测）：
 *   - DS / Jailed / Escaped 变体 → 含链（第 1/2 代）
 *   - FilzaSlop v ≤ 1.0.2 → 含链（第 1/2 代）
 *   - FilzaSlop v ≥ 1.0.3 → 无链（第 3 代）
 *   - Filza_4.0.x（NoUS/Crack）裸壳 → 不可注入，返回 null
 *
 * ★ 这是【文件名侧推断】，非 dylib 字符串指纹实测；无法判定时返回 null（不编造）。
 * @returns {{generation:'gen12'|'gen3'|null, needsKernel:boolean|null, version:number[]|null}}
 */
export function classifyArtifact(name) {
  const n = String(name || '');
  // 裸壳（备壳输入，无 dylib 无载入命令）⇒ 不分类
  if (/Filza_4\.0|NoUS|Crack/i.test(n)) {
    return { generation: null, needsKernel: null, version: null };
  }
  const v = versionFromFilename(n);
  // DS / Jailed / Escaped 变体 → 含链
  if (/DS|Jailed|Escaped/i.test(n)) {
    return { generation: GENERATIONS.GEN12, needsKernel: true, version: v };
  }
  // FilzaSlop：断点 1.0.2 → 1.0.3
  if (v) {
    if (cmp3(v, [1, 0, 3]) >= 0) return { generation: GENERATIONS.GEN3, needsKernel: false, version: v };
    if (cmp3(v, [1, 0, 2]) <= 0) return { generation: GENERATIONS.GEN12, needsKernel: true, version: v };
  }
  return { generation: null, needsKernel: null, version: v };
}
