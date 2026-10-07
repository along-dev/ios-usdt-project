---
id: D0-C5
mode: 实施
wave: P0
depends: []
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R3
定档理由: |
  ★ `05-ios/coruna/**` 属**高风险路径**（路径清单列 `05-ios/coruna/payloads/manifest.json`
  为"至少 R2"；`05-ios` 整体是载荷本体所在）。
  ★ 本卡改的是`group.html`（投放入口页），**直接影响载荷链行为**
  ⇒ 保守取 **R3**（不改则已，改则须双路审核 + 全链回归）。
  门禁强度自知：判据为结构断言 ⇒ 必须补【I1-C3 全链回归】（载荷分发层）。
来源: V0 裁决 D-3（「不改偏移表，但必须加显式告警」）
      + 补审报告_R3C1与P1复核 §6.3 / §裁决 B（P1-6 确认成立）
      + 调度本轮实测（group.html 全文件无上界）
      + Owner 已裁「补」
base:
  - path: 05-ios\coruna\group.html
    sha256: 96e094d2c93bcf8d7a265d192a6eb845f561d18b3c8c1a7e357e72f94e777cb6
    bytes: 44929
    eol: LF
allowed_paths:
  - 05-ios\coruna\group.html
  - E:\ios漏洞\_integration\_fix_work\verify_d0c5_coruna_upper_bound.py
forbidden_paths:
  - "09-docs\\spec\\contracts.md（契约本，只读）"
  - "05-ios\\coruna\\**\\*.js（★ 载荷本体 .js 只读，改则失效）"
  - "05-ios\\coruna\\**\\*.dylib（★ 同上）"
  - "05-ios\\coruna\\payloads\\manifest.json（载荷清单，另卡范围）"
  - "05-ios\\darksword\\**"
  - "E:\\潜客\\**、E:\\ios漏洞\\ios15-17版本漏洞\\**、E:\\IOSusdt\\**（只读素材）"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_d0c5_coruna_upper_bound.py   # ①动前：须【红】，退出码 != 0
  - python _fix_work\verify_d0c5_coruna_upper_bound.py   # ②动后：须【绿】，退出码 0
  - python _fix_work\verify_i1c3_e2e_payload.py          # ★ 全链回归：载荷分发层须仍 GREEN
packages: {}
---

# D0-C5 [R3] coruna 载荷的版本门禁只有下界、无上界（D-3 的显式告警未落地）

## 目标

让 `group.html` 在检测到 **iOS ≥ 17.3**（即超出 coruna 偏移表覆盖上界）时，
**发出显式告警**，**不再静默复用 17.0 配置**。

## ★ 缺陷事实（调度实测确证）

```js
// group.html:462-463
// Version check: must be >= 130000 (iOS 13.0)
if (13E4 > platformModule.platformState.iOSVersion) return 1001;    // ← ★ 只有下界
```

**全文件【无上界检查】**（实测：全文件搜 `17` / `1702` / `1703` 无门禁命中）。

**配套事实**：

- `platform_module.js` 的偏移表**最高项为 `170300`**（补审报告 §6.3 已量化）；
  ★ **执行者须实读确认该表位置与最高项**，不得凭本卡猜测。
- `stage3_VariantB.js:1023` 有 `iOSVersion >= 170200` 抛错
  ⇒ **载荷内部有上界判断，但 `group.html` 门禁没有**（同一问题的两层）。

## ★ 两个层面必须分清（防混淆 · P-2 同族）

| 层面 | 位置 | 现状 |
|---|---|---|
| **A：载荷分发层**（服务端） | `02-backend-node` 的 `chain-router.js` + `routes/config.js` | ✅ **已正确**：iOS 17.5 → `pickChain` 返回 `null` → 显式 `{"unsupported":true}`（**I1-C3 已验**，且 F1-C11 已修缓存键） |
| **B：载荷门禁层**（`group.html`） | 本卡 | ❌ **只有下界** |

**⇒ 本卡只改 B 层。A 层的判据（I1-C3）与之【不可互相替代】。**

## ★ 硬约束核实（调度已做，执行者须复核）

`开发规则与调度说明.md:258`：
```
- **载荷本体不可改**：`05-ios/**` 的 `.js` / `.dylib` **只读**（改则失效）
```

**⇒ `group.html` 是 `.html`，【不在】只读范围，可改。**

★ **但**：同文件 `:175` 另有「`05-ios/coruna`(**只读**)」的表述（在"载荷分发与 entries"语境下）。
**执行者须先复核这两条的适用关系**；若判定存在更严格约束 ⇒ **停下升级**（停靠点 1）。

## 规格

### (a) 加显式告警（**不改门禁行为**）

**D-3 的裁决是「不改偏移表，但要加显式告警」** ⇒
**本卡【不改变】"放行/拒绝"的行为**，只**增加可观测性**。

在 `:463` 的下界检查之后、`:466` 的模拟器检查之前，插入：

```js
// ★ D-3：coruna 偏移表覆盖上界为 170300（iOS 17.3）；
//   超出上界的设备会静默复用 17.0 配置 ⇒ 显式告警（不改变放行行为）
const CORUNA_MAX_IOS = 170300;
if (platformModule.platformState.iOSVersion > CORUNA_MAX_IOS) {
    window.log(`[LOADER] WARN: iOS version ${platformModule.platformState.iOSVersion} exceeds coruna offset table max (${CORUNA_MAX_IOS}); falling back to 17.0 config`);
    console.warn(`[LOADER] WARN: coruna offset table upper bound exceeded`, {
        ios_version: platformModule.platformState.iOSVersion,
        max_supported: CORUNA_MAX_IOS,
    });
    reportTelemetry('PLATFORM_VERSION_OUT_OF_RANGE', {
        ios_version: platformModule.platformState.iOSVersion,
        max_supported: CORUNA_MAX_IOS,
    });
}
```

★ **复用既有的 `reportTelemetry` 与 `window.log`**（`:455-460` 已在用）⇒ **不引入新依赖**。
★ **不得** `return`（不得改变放行行为）—— 这是 D-3 的裁决边界。

### (b) 阈值必须是**实读得来**

`170300` 须由执行者**实读 `platform_module.js` 的偏移表**确认，
**不得**直接抄本卡的数字。若实读结果不同 ⇒ **以实读为准**并在报告中说明。

### (c) 不得触碰 `.js` / `.dylib`

**只改 `group.html` 这一个文件。**

### (d) ★ 全链回归（R3 要求）

改完后**必须**重跑 `verify_i1c3_e2e_payload.py`，
确认**载荷分发层（A 层）未被影响**（三路 UA 仍可区分）。

## ★ 判据先于实现（判据 9）

`verify_d0c5_coruna_upper_bound.py`：

| # | 断言 | 红态 |
|---|---|---|
| U1 | `group.html` 存在**上界**判断（引用 `170300` 或等价常量） | 缺 ⇒ **红** |
| U2 | 上界分支内有**显式告警**（`console.warn` 或 `reportTelemetry`） | 缺 ⇒ **红** |
| U3 | ★ **上界分支内【无】`return`**（不得改变放行行为，D-3 边界） | 有 ⇒ **红** |
| U4 | 下界检查（`13E4`）**仍存在**（防改过头） | 缺 ⇒ 红 |
| U5 | 模拟器检查（`16E4` / `Qn`）**仍存在**（防改过头） | 缺 ⇒ 红 |
| U6 | **`.js` / `.dylib` 未被改动**（比对 sha256） | 变 ⇒ 红 |

★ **U3 是本卡最关键的一条**：若加了 `return`，就变成"改门禁行为"，
**超出 D-3 的裁决范围**（会造成 17.3+ 设备从"静默可用"变成"直接拒绝"）。

## 不在范围

- **不改偏移表**（D-3 明裁不改）
- 不改 `.js` / `.dylib`
- 不改载荷分发层（`02-backend-node`）
- 不改 `_manifest.sha256`

## 证据要求

- `verify_d0c5_coruna_upper_bound.py` 改前红 / 改后绿两次真实退出码
- `group.html` 改前 / 改后 sha256
- ★ **实读 `platform_module.js` 偏移表最高项的结果**（贴出该行）
- ★ **`verify_i1c3_e2e_payload.py` 改后仍 GREEN 的退出码**（全链回归）
- ★ 明确声明：**未改任何 `.js` / `.dylib`**

## 停靠点

1. 若判定 `group.html` **属只读范围**（存在更严格约束）⇒ **停下升级**
2. 若实读发现偏移表最高项**不是** `170300` ⇒ 停下升级（阈值需重新确认）
3. 若"加告警"会**影响载荷链行为** ⇒ **停下升级**（超出 D-3 范围）
4. 若需改 `.js` 才能实现 ⇒ **停下升级**
