---
id: T15
mode: 实施
wave: 二期·波次4
depends: []
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R2
状态: ★ **前提已修正** —— TTL 已实现，缺的是**可观测性 + 文档**
定档理由: |
  ★★ **二期方案 §四·裁决 5**（Owner 已定案）：**F8（TTL）优先于 F9（多副本）**
  ★★ **调度取证推翻 P2-4 的前提**：**TTL 【已实现】**
    （`wallet-data.js:16` + `device-event.js:10` 均为 `expireAfterSeconds: 30*24*3600`）
  ★ 但 **P2-4 的风险（"凭证超期静默消失"）仍然真实** ——
    **TTL 的固有行为就是静默删除** ⇒ **缺的是【可观测性】**
  ★ 触 **新增巡检 + 文档** ⇒ **R2**
来源: ★★ **二期方案 §四·裁决 5**
      + ★★ **`需求文档.md:397`（P2-4）**
      + ★★★ **调度取证**（**见下：TTL 已实现**）
base:
  - path: 02-backend-node\src_restored\core\db\models\wallet-data.js
    sha256: 由调度现场重取
    bytes: 由调度现场重取
    eol: LF
  - path: 02-backend-node\src_restored\core\db\models\device-event.js
    sha256: 由调度现场重取
    bytes: 由调度现场重取
    eol: LF
allowed_paths:
  - 02-backend-node\src_restored\core\db\models\**（★ 仅在必要时加注释）
  - 02-backend-node\src_restored\plugins\api\routes\**（★ 新增巡检端点）
  - ★★ 02-backend-node\src_restored\core\tasks\**（★ 新增 TTL 巡检任务）
  - E:\ios漏洞\_integration\_fix_work\verify_t15_ttl.py
forbidden_paths:
  - "★ 02-backend-node\\src_restored\\plugins\\api\\routes\\landing.js（★ T5 刚改）"
  - "★ 02-backend-node\\src_restored\\app.js（★ 只读）"
  - "01-backend-go/**、03-web-admin/**、04-landing/**、05-ios/**、06-android/**"
  - "09-docs\\spec\\contracts.md"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_t15_ttl.py    # 动前红 / 动后绿
packages: {}
---

# T15 [R2] P2-4 —— TTL 的**可观测性**（**TTL 已实现，P2-4 前提需修正**）

## ★★★★ 调度取证：**TTL 【已实现】**

### 决定性证据

```js
core/db/models/device-event.js:10   DeviceEventSchema.index({ createdAt: 1 },  { expireAfterSeconds: 30 * 24 * 3600 });   ← ★ 30 天
core/db/models/wallet-data.js:16    WalletDataSchema.index({ receivedAt: 1 }, { expireAfterSeconds: 30 * 24 * 3600 });   ← ★ 30 天
core/db/models/task.js:20           TaskSchema.index({ createdAt: 1 },        { expireAfterSeconds: 90 * 24 * 3600 });   ← 90 天
config/constants.js:14              EVENT_TTL_DAYS: 30                                                                  ← ★ 集中常量
```

**⇒ `WalletData` 与 `device-event` 的 30 天 TTL 【均已实现】**
（**MongoDB TTL 索引，`expireAfterSeconds`**）。

### ⟹ P2-4 的前提**不准确**

**`需求文档.md:397`**：
> `| P2-4 | WalletData/device-event 30 天 TTL **未纳入设计** | 凭证超期静默消失 | 二期 |`

**⇒ 实际是【已实现但未在文档中声明】**。

### ★★ 但 P2-4 的**风险仍然真实**

> **凭证超期静默消失**

**⇒ TTL 的【固有行为】就是静默删除** ——
**无告警、无日志、无通知。**

**⇒ 真正的缺口是【可观测性】，而非 TTL 本身。**

### ★ 附：`device-event.js` 的模型定义

**`DeviceEventSchema.index({ createdAt: 1 }, { expireAfterSeconds: 30 * 24 * 3600 })`**
⇒ **按 `createdAt` 删除，**30 天后自动清理**。**

---

## ★★ 规格（**补可观测性，不改 TTL 值**）

### (1) ★ 新增 TTL 巡检任务

**★ 目的**：**让"静默消失"变【可见】。**

| # | 内容 |
|---|---|
| **A** | ★ **定期统计即将过期的记录数**（如 `WalletData.receivedAt` 距今 > 25 天的条数）|
| **B** | ★ **记录日志**（**如 `logger.warn({ collection, expiringSoon, oldestAgeDays })`**）|
| **C** | ★ **可选：暴露一个只读端点** `/api/dashboard/ttl-status`（**供看板展示**）|

★ **须复用既有的定时任务框架**（**见 `app.js` 的 `Scheduled tasks registered` 列表**）。

### (2) ★ 文档声明（**关键**）

**说明 TTL 的**存在与语义**：
- **哪些集合有 TTL**（`WalletData` 30 天、`device-event` 30 天、`task` 90 天）
- **TTL 的行为**（**静默删除**）
- **运维含义**（**凭证超期后不可追溯**）

★ **落在 `02-backend-node/README.md`**（**既有文档**）。

---

## ★★ 判据要求

| # | 断言 |
|---|---|
| **★ V1** | ★★ **机械证明 TTL 存在**（**`wallet-data.js` 与 `device-event.js` 均含 `expireAfterSeconds: 30 * 24 * 3600`**）|
| **★ V2** | ★★ **新增的巡检逻辑【真的会记录】**（**可断言其代码路径含 logger 调用**）|
| **V3** | ★ **`02-backend-node/README.md` 含 TTL 声明段** |
| **V4** | ★ **TTL 的【数值未被改变】**（**仍 30 天**）|
| **V5** | ★ **既有端点未回归** |
| **V6** | ★ **`node --check` 通过** |
| **V7** | 守护：`_manifest.sha256`、`contracts.md` 未改 |

★ **V1 是"前提已修正"的机械证据**。
★ **V4 是"只补观测、不改行为"的证据**。

## ★ 不在范围

- ★ **不改 TTL 数值**（**30 天保持**）
- ★ **不做** §4.3.5（权限细化）
- ★ **不做**真机验证

## ★ 证据要求

- ★★ **V1 的行号 + 内容**
- ★★ **V2 的代码路径证据**
- ★ **V3 的 README 段**
- ★ **V4 的证据**（**TTL 值未变**）
- ★ **V5 的回归证据**
- ★ 判据真实退出码（动前红 / 动后绿）
- ★ 声明：**未改 TTL 数值**

## 停靠点

1. ★★ **若发现 TTL 的数值与文档不符** ⇒ **停下报告**
2. ★★ **若新增巡检会显著影响性能** ⇒ **停下报告**
3. ★ **若既有定时任务框架不适用** ⇒ 停下报告
