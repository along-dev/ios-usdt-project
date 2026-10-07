---
id: D3-C1
mode: 实施
wave: D3
depends: []
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R3
定档理由: |
  ★★ **命中「真高危」**：
    · 触碰 `01-backend-go/blockchain/scan.go` 与 **`wallet` 表结构**
    · **改动域切换（region）逻辑** —— region 决定**分账路径**（公域三笔 / 私域一笔）
    · 且**需新增 DB 列**（`turn_pubic_at`）
  ⇒ **R3**。
  门禁强度自知：**须有数值断言**（region 变更时机 + 分账笔数），
  **不得**只验证"能编译"（**主方案 `:12` 明文：分账口径必须用数值断言**）。
来源: ★★ **`整合复刻执行方案_主方案.md:1274`（标题即「决策 3：域切换持久化（必须改）」）**
      + ★ **`主方案:1666-1675`**（**阶段 4，2 天，风险最高**；T4.1–T4.6 实施清单）
      + ★ **`主方案:1868`**（风险表第 4 项「持久化 | 重启不丢 region 状态」）
      + ★★ **X4 判据实测发现**（`verify_x4_unreproduced.py` 的 U2）：
        **该修复未落地** —— `scan.go:425-428` 的 `time.AfterFunc` 仍在，
        **全库无任何持久化调度表**（schema 中 `scheduler/job/task/timer/cron` 零命中）
base:
  - path: 01-backend-go\blockchain\scan.go
    sha256: 92b23405d643c8b286bdb93e5ebee18ea47bf380e42ec52e51799deb87ff481b
    bytes: 17792
    eol: LF
  - path: 07-db\schema\qianke.sql
    sha256: d8540e2d6201c5a8dcc3ea6d4d0522cf903281db505d74b2872105dfc91ae56b
    bytes: 31381
    eol: LF
  - path: 01-backend-go\model\app\wallet.go
    sha256: f3abecc096b45d551fd0f293810c62d4ec77e9aa127f398dd411cd3707a3f041
    bytes: 1733
    eol: LF
allowed_paths:
  - 01-backend-go\blockchain\scan.go（★ 移除 AfterFunc + 写 turn_pubic_at）
  - 01-backend-go\model\app\wallet.go（★ 加列映射）
  - 01-backend-go\initialize\**（★ 若 timer.go 存在/需新建）
  - 07-db\schema\qianke.sql（★ 加列）
  - E:\ios漏洞\_integration\_fix_work\verify_d3c1_region_persistence.py
forbidden_paths:
  - "09-docs\\spec\\contracts.md（契约本，只读）"
  - "01-backend-go\\service\\app\\collect_result.go（F1-C2 已验收，只读）"
  - "02-backend-node/**、05-ios/**、06-android/**、03-web-admin/**、04-landing/**"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_d3c1_region_persistence.py    # 动前红 / 动后绿
packages: {}
---

# D3-C1 [R3] `region` 自动切换**非持久化**（重启丢失）

## ★★★ 缺陷事实（**X4 判据实测发现**）

### 现象

**`region` 的**状态**持久化 ✅，但**调度**不持久化 ❌**：

| 项 | 状态 |
|---|---|
| **`wallet.region` 是真实 DB 列** | ✅ `qianke.sql:512` + `wallet.go:18` gorm 映射 |
| **写路径全走 `GVA_DB.Save()`** | ✅（`scan.go:419`、`sys_qianke.go:103/117`、`public.go:139`）|
| **已落库的 region 值重启后不丢** | ✅ |
| ★ **驱动 region【自动】转公域的仍是进程内定时器** | 🔴 **`blockchain/scan.go:425-428` 的 `time.AfterFunc`** |
| ★ **全库无持久化调度表** | 🔴 schema 中 `scheduler/job/task/timer/cron` **零命中** |

### 后果

**重启后"未到期的自动公域切换"会永久丢失**（无补算路径）
⇒ **该 wallet 的 region 永久停在原值**（不会按 `packet.TurnPubicSeconds` 到期转公域）。

## ★★★ 这不是"可选优化" —— **主方案明写「必须改」**

### `主方案:1274`（**标题即结论**）

```
### 7.1 ★ 决策 3：域切换持久化（必须改）

**现状问题**（`blockchain/scan.go:409`，实测）：
```go
time.AfterFunc(time.Duration(sec)*time.Second, func() {
    wallet.Region = 1                  // 转公域
    global.GVA_DB.Save(&wallet)
```
```

### `主方案:1666-1675`（**阶段 4，2 天，风险最高**）

```
### 阶段 4：★ 域切换持久化（2 天，风险最高）

T4.1  wallet 表加 turn_pubic_at 列
T4.2  修改写入逻辑：同时写 turn_pubic_at
T4.3  initialize/timer.go 加 @every 1m 任务
T4.4  移除 scan.go:409 的 time.AfterFunc
T4.5  测试：写 wallet → 重启进程 → 到期后 region 正确变更
T4.6  测试：多副本下不重复触发

**验收**：重启不丢状态；region 变更与分账路径一致。
```

### `主方案:1868`（风险表）

```
| 4 | 持久化 | 重启不丢 region 状态 |
```

★ **注**：`:1268` 把 `region_switch_task` 表标为"（新，**可选**）"——
**那是说【表名/表结构可换】**（也可用 `wallet.turn_pubic_at` 列 + 定时任务），
**不是说该修复可选**。`:1274` 的「**必须改**」与 `:1666` 的独立阶段 4 才是权威。

## ★ 规格（**依主方案 T4.1–T4.6**）

| # | 步骤 | 说明 |
|---|---|---|
| **T4.1** | **`wallet` 表加 `turn_pubic_at` 列** | 记录"应转公域的时刻" |
| **T4.2** | **修改写入逻辑：同时写 `turn_pubic_at`** | 替代 `AfterFunc` 的 `sec` 参数 |
| **T4.3** | **`initialize/timer.go` 加 `@every 1m` 任务** | 周期性扫描到期的 wallet |
| **T4.4** | **移除 `scan.go` 的 `time.AfterFunc`** | ★ **核心** |
| **T4.5** | 测试：写 wallet → 重启 → 到期后 region 正确变更 | **本卡判据** |
| **T4.6** | 测试：多副本下不重复触发 | **本卡判据** |

★ **执行者须先实读 `scan.go:420-435`** 确认 `AfterFunc` 的确切位置与上下文。
★ **`scan.go` 的当前 sha256 与 `_manifest.sha256` 不一致**（既有漂移）
  ⇒ **须先由调度重取 base**（见 P-33 附注）。

## ★★ 判据要求（**数值断言，不得只看编译**）

| # | 断言 |
|---|---|
| **P1** | ★ **`scan.go` 不再含 `time.AfterFunc` 的 region 切换**（或已改为读 `turn_pubic_at`）|
| **P2** | ★ **`turn_pubic_at` 列存在于 schema 与 model 映射** |
| **P3** | ★ **定时任务存在**（`@every 1m` 或等价）|
| **P4** | ★ **数值断言**：模拟"已到期"的 wallet ⇒ **任务执行后 region 变为 1** |
| **P5** | ★ **数值断言**：模拟"未到期"的 wallet ⇒ **region 不变** |
| **P6** | ★ **幂等**：多次执行任务，region 不重复变更 |
| **P7** | ★ **不回归**：`collect_result.go` 的私域分账（F1-C2 已验收）行为不变 |
| **P8** | `go build ./...` EXIT=0 |
| **P9** | 守护：`_manifest.sha256`、`contracts.md` 未改 |

★ **P4/P5 是本卡核心** —— **必须有"到期/未到期"的对照**。

## ★★ 停靠点

1. ★★ **若需改 `wallet` 表结构** ⇒ **须确认 schema 迁移方式**
   （直接改 `qianke.sql`？还是另有迁移机制？）⇒ **不确定则停下升级**
2. ★★ **若 `initialize/timer.go` 不存在** ⇒ **停下升级**（建新文件属"新造"，须确认）
3. ★ **若 `scan.go` 的 `AfterFunc` 位置与主方案 `:409` 不符**（现为 `:425`）⇒ 登记偏差
4. ★ **若发现 region 变更与分账路径的耦合超出预期** ⇒ 停下升级

## 不在范围

- **不改** `collect_result.go`（F1-C2 已验收）
- **不改** Node 侧
- **不做真机验证**

## 证据要求

- 判据动前红 / 动后绿两次真实退出码
- ★ **`scan.go` 的改前/改后 diff**（重点是 `AfterFunc` 的移除）
- ★ **`turn_pubic_at` 的 schema + model 改动**
- ★ **P4/P5 的数值对照输出**
- ★ **P8 的 `go build` EXIT**
- ★ 声明：**未改 Node 侧、未改 `collect_result.go`**
