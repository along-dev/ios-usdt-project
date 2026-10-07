# 模板层占位符登记表（W1-C1b）

★ 本目录 `05-ios/_templates/` 是【模板层】，与 `05-ios/{coruna,darksword}/`（载荷本体，只读）
  **物理隔离**。打包期由 `build_unified.ps1` 的 `Invoke-TemplateInjection` 注入真值后写出产物。

## 方向说明

| 方向 | 机制 | 位置 |
|---|---|---|
| **脱敏**（既有） | 真值 → 占位符 | `build_unified.ps1` 的 `$SANITIZE_LEGACY_REPLACEMENTS` |
| **注入**（本卡） | 占位符 → 真值 | `build_unified.ps1` 的 `Invoke-TemplateInjection` |

两者方向相反、机制相同（同一张"值 ↔ 占位符"映射表），互为逆运算。

## 首批占位符

| 占位符 | 语义 | 真值来源（环境变量） | 承接卡 | 必填 |
|---|---|---|---|---|
| `__C2_ENDPOINT__` | C2 域名（含 scheme） | `W1C1B_C2_ENDPOINT` | D0-C7 | 是 |
| `__RCE_MAX_ATTEMPTS__` | RCE 重试次数 | `W1C1B_RCE_MAX_ATTEMPTS` | S2 | 是 |

★ 真值一律从**环境变量**读取，**绝不硬编码进脚本**（否则即为新的明文泄漏）。
★ 占位符未被替换（真值缺失）⇒ **报错退出**，绝不静默产出含占位符的产物。

## 承接卡待补

| # | 占位符 | 承接卡 | 状态 |
|---|---|---|---|
| 1 | `__C2_ENDPOINT__` | D0-C7 | 语义已定，值由 D0-C7 填 |
| 2 | `__RCE_MAX_ATTEMPTS__` | S2 | 语义已定，值由 S2 填 |
| 3 | （S1 的 404 竞态） | S1 | ★ 待定位 |
| 4 | （S3 的入口 9 步合并） | S3 | ★ 待定位 |

## 模板清单

| 模板 | 派生自 | 含占位符 |
|---|---|---|
| `darksword/rce_loader.template.js` | `05-ios/darksword/rce_loader.js`（只读） | `__C2_ENDPOINT__`、`__RCE_MAX_ATTEMPTS__` |

★ **`coruna/` 目录为空是【有意】的**（Owner 裁定⑨，⌛2026-10-03）：
  coruna 链**没有只读真值需要脱敏/注入** ⇒ **无派生目标，故无模板**。
  取证：① `group.html` 全文**无 C2 域名字面量**（C2 base 由 `window.location.origin` 运行时派生）；
  ② 交付载荷 `templates/coruna/` 的 15 个 `.js` 除 `w3.org` XML 命名空间外**无 host 真值**；
  ③ coruna 的真值全在**非交付面** —— 管理台路径 `group.html:242`、salt `group.html:466` /
  `chain-coruna.js:230`、`coruna/backend/*.py`（AES key、遥测外联）。
  ★ **不得据此认为 coruna 模板"缺失待补"** —— 见 `W-IOS-GAP-模板层空目录与HOST占位符-取证与处置.md` §1。
