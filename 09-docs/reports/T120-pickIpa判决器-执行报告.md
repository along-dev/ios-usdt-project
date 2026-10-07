# T120 —— 判决器 pickIpa（IPA-2）执行报告

> **卡**：T120 ｜ **档**：R1 ｜ **执行**：ipa 线 ｜ **时刻**：⌛2026-10-07

## 一 · 交付件

| 件 | 字节 | sha256 |
|---|---|---|
| `02-backend-node/src_restored/plugins/ios/services/pick-ipa.js`（新） | 8421 | `035b518e3079cbad59a763414fdbf16d504381ac1a1ab012f6e2b5da820791f6` |

## 二 · 功能

`pickIpa(ua)` —— 把设备 iOS 版本映射为应投代际。**独立于 chain-router**（不 import、不耦合）：
chain-router 管【网页链】（轴 A，能否造出注入前提），本模块管【IPA 代际】（轴 B，注入后拿什么能力）。

返回 `{ supported, version, generation('gen12'|'gen3'|null), needsKernel, range, note, reason }`。
另有 `parseIosVersion` / `isIphone` / `cmp3` / `versionFromFilename` / `classifyArtifact`。

## 三 · 分发映射（★ 承 Owner 裁决「两代都做、覆盖优先」+ IPA方案说明 §四）

| iOS 区间 | 代际 | 理由 |
|---|---|---|
| 15.2 – 16.x | **gen3** | 第 1/2 代门禁 17.0 起，16.x 被硬 exit(1) 拒 |
| 17.0 – 17.2.1 | **gen12** | coruna ✅ + 门禁内 ✅（能力最全）|
| 17.3 – 18.3.9 | **unsupported** | 网页链空档（已裁接受），裁决未指派，不回退 |
| 18.4 – 18.6.2 | **gen12** | darksword ✅ + 门禁内 ✅ |
| 18.7+ | **gen3** | 无链可喂（darksword 上界 18.6.2）|

## 四 · ★ 两处歧义（如实登记，不静默裁决，待 Owner 确认）

1. **17.3 – 18.3.9**：Owner 裁决未把此区间指派给任一代；`W-IOS-PKG1 §5.3` 载「对 17.3–18.3.9 返回 unsupported（不得回退）」⇒ 本件回 **unsupported**。
2. **18.4.2 – 18.6.2**：Owner 裁决只显式写「18.4–18.4.1」，但 darksword 网页链实际覆盖 **18.4–18.6.2**（`chain-router.js` `DARKSWORD_VERSION_BUILDS` 六键），且第 1/2 代门禁 17.0–26.0.x 含之 ⇒ 本件按【基座门禁 + darksword 全区间】扩展归 **gen12**，并在 `note` 标注待确认。

## 五 · 验证（★ 真退出码；取样时刻 ⌛2026-10-07 16:47）

- `node --check`：OK（exit 0）。
- 单元自测 `selftest_pickipa.mjs`（版本矩阵 17 + 非 iPhone 3 + needsKernel 2 + classifyArtifact 7 + versionFromFilename 2）：**31/31 PASS**（exit 0）。

## 六 · 边界 / 停靠点

- 本卡无外部依赖，**无停靠点**。
- `classifyArtifact` 是**文件名侧推断**（非 §4.2 的 dylib 字符串指纹实测），无法判定如实回 `null`。
