---
id: T2
mode: 文档
wave: 二期·波次1
depends: []
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R0
定档理由: |
  ★★ **源卡（二期方案 §三·波次1）给出档位：`R0`** —— **纯文档更正，无代码改动**。
  ★ 依据源卡 `R2-C4` 的先例：「纯文档收口，无代码改动，判据为 grep 断言 ⇒ R0 不派独立审核」。
  门禁强度自知：**须有实测证据**（**行号 + 引用**），不得只引文档。
来源: ★★ **二期方案 `§三·波次1` T2**
      + ★★★ **调度取证**：`需求文档.md:106/113/119/120` vs
        `app.js:18/70/88-98` + `plugins/c2/index.js`（**109 行**）
base:
  - path: 09-docs\analysis\需求文档.md
    sha256: 1f402524add44db56a44791d6b43c595e27a099b294d521cb1dd4dff877f7567
    bytes: 22455
    eol: LF
    note: ★ 本值是 **T1 之后**的值（T1 已改过本文件）
allowed_paths:
  - 09-docs\analysis\需求文档.md（★ 更正 :106 与 §3.3）
forbidden_paths:
  - "★ 全部产物代码（01–06）"
  - "09-docs\\spec\\contracts.md"
  - "_manifest.sha256"
verify:
  - 更正后无「不在 E:\USDT项目 内」「entries 恒空」的矛盾陈述
packages: {}
---

# T2 [R0] `chain-router.js` 接入的**边界收口**（文档更正）

## ★★★ 调度取证（**决定性**）

### 产物实际

**`02-backend-node/src_restored/app.js`**：

```js
:18  import { c2Plugin } from './plugins/c2/index.js';
:70  await fastify.register(c2Plugin);        ← ★★ 生产调用点【存在】

:88  /**
:89   * ★ I1-C2：把 coruna / darksword 的【模块】注册为 Payload 条目（entries 的来源）。
:91   * 背景：initPayloads() 只注册 templates/payloads/*.dylib（名如 a1lib），
:92   * 而 config-builder 的 entries 用 moduleBelongsToChain 过滤 ⇒ 那些 dylib 名全部为 false
:93   * ⇒ ★【entries 恒空】（契约 C-3 的红态来源）。
:94   * 本函数从 templates/coruna/ 的【产物内副本】派生条目（契约 C-4 (b)）
:97   * ★ 失败必须显式（不得静默吞）—— 否则 entries 静默为空，正是 P-1 形态。
:98   */
:99  async function syncChainPayloads() { ... }
```

★ **注意 `:88-98` 的注释本身就是在描述【该红态已被 I1-C2 解决】**
（"所谓红态来源" ≠ "当前仍红"；该函数**正是为了解决它而存在**）。

**`02-backend-node/src_restored/plugins/c2/index.js`**（**109 行**）：

```js
:5-13  9 个路由 import（alive/activate/event/upload/telemetry/config/payload/ip-sync/task）
:14    import { collectorPlugin } from '../collector/index.js';
:15    export async function c2Plugin(fastify) {
:17        fastify.addHook('preParsing', ...)      ← ★ 真实业务逻辑
```

**`chain-router.js`**（**203 行**）的导出：
`CHAINS` / `DARKSWORD_VERSION_BUILDS` / `SBX0_COVERED_BUILDS` /
`DARKSWORD_186_RCE_STUB` / `darkswordStageReach` / `parseIosVersion` / `isIphone` /
`pickChain` / **`moduleBelongsToChain`**

**被 3 个模块 import**：
`plugins/c2/routes/config.js`、`services/config-builder.js`、`services/chain-coruna.js`

### ★★ 文档的三条陈述（**全部与产物矛盾**）

| # | 文档陈述 | **产物实际** | 判定 |
|---|---|---|---|
| **1** | **`:106`**「`chain-router.js` 等 4 个文件**不在 `E:\USDT项目` 内**」 | 在 **`02-backend-node/src_restored/plugins/c2/`** | ❌ **假** |
| **2** | **`:119`**「接通该线需在 `app.js` **新增调用点**」 | **`:70` 已存在** `await fastify.register(c2Plugin)` | ❌ **假** |
| **3** | **`:120`**「**`entries` 恒空**」（**接受代价**） | **`:88-98` 明确说该红态【已被 I1-C2 解决】**；**C-3 判据（`verify_entries_coruna.mjs`）GREEN** | ❌ **假** |

**⇒ 三条【全部过期】。**

---

## ★★ 规格（**本卡只做文档更正**）

### 更正 1：`需求文档.md:106`（§3.1 验收项 1.6）

**原文**：
```
| 1.6 | ~~iOS 两条链可被正确路由~~ **→ 已裁决降为二期（2026 本轮，见 §3.3）**
| **不再作为一期验收项**。原验收说明保留作溯源：原型已验证（源侧）；
  产物未接入 —— `chain-router.js` 等 4 个文件**不在 `E:\USDT项目` 内**；59…
```

**⇒ 更正为**（**加"实测已接入"的更正注**）：
```
| 1.6 | ~~iOS 两条链可被正确路由~~ **→ 曾裁决降为二期（见 §3.3）**；
  ★★ **实测更正（二期 T2）**：产物**已接入** —— `app.js:18/70`
  `import { c2Plugin }` + `await fastify.register(c2Plugin)`；
  `chain-router.js` **在** `02-backend-node/src_restored/plugins/c2/`（**非"不在项目内"**）；
  **C-3 判据 GREEN**（`entries` 15/5 实测通过）
```

### 更正 2：`需求文档.md:113-121`（§3.3 裁决）

**加"实测更正块"**，列出三条与产物矛盾的陈述。

---

## ★ 判据要求

| # | 断言 |
|---|---|
| **V1** | ★ 更正后**无**「不在 `E:\USDT项目` 内」的**未加注**陈述 |
| **V2** | ★ 更正后**无**「`entries` 恒空」的**未加注**陈述 |
| **V3** | ★ **含实测证据**（`app.js:18/70` 的引用）|
| **V4** | ★ **未改任何产物代码** |
| **V5** | 守护：`_manifest.sha256`、`contracts.md` 未改 |

## ★ 不在范围

- ★ **不改产物**（**接入已完成，非本卡任务**）
- ★ **不拆 `c2Plugin`**（**拆除会让 C-3 重新变红**）

## ★ 证据要求

- ★ **改前/改后 diff**
- ★ **实测证据**（`app.js` 的行号引用）
- ★ 声明：**未改产物**
