---
id: F1-C10
mode: 验证
wave: 2
depends: [F1-C8, F1-C9]
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R3
定档理由: |
  本卡是【判据级】产出 —— 按调度 §五「判据级 → 命中即 R3」。
  且它是 **W2-C3（桥 fail-open 修复）至今唯一缺失的回归保护**：
  P0-3 逃逸的原因被原报告明确记为「e2e 直接打 Go API，从未经过 Node 桥」，
  该盲区至今仍在（I2-C1 亦未覆盖 —— 见 L007 §5）。
  门禁强度自知：必须**从 Node 侧真实调用**并断言「Go 返回 code!=0 时桥判为失败」，
  不得用静态读取 `okBusiness` 源码冒充。
来源: L007 §5 与 §12（I2-C2 覆盖率矩阵 §八 #1 项）+ Owner 本轮裁决「裁决 a」
base:
  - path: 02-backend-node\src_restored\core\collect-bridge.js
    sha256: 需调度现场重取
    bytes: 需现场重取
    eol: 需现场确认
allowed_paths:
  - E:\ios漏洞\_integration\_fix_work\verify_f1c10_bridge_e2e.mjs
forbidden_paths:
  - "全部产物代码（★ 纯验证卡）"
  - "09-docs\\spec\\contracts.md"
  - "_manifest.sha256"
verify:
  - node _fix_work\verify_f1c10_bridge_e2e.mjs    # 须【绿】，退出码 0
packages: {}
---

# F1-C10 [R3] Node 桥端到端业务判据（P0-3 的回归保护）

## 目标

建立**唯一一条经过 Node 桥**的端到端断言，证明：
**当 Go 侧返回业务失败（`code != 0`）时，桥也判为失败** —— 而不是 fail-open。

## 为什么必须有这张卡

| 事实 | 出处 |
|---|---|
| `W2-C3` 修的正是桥的 fail-open（原用 `r.ok` 判成败） | `collect-bridge.js:76-87` |
| **P0-3 逃逸的原因**：「e2e 直接打 Go API，**从未经过 Node 桥**」 | 原审核报告 §五 |
| I2-C1 **复现了同一盲区**：只验了 Go 侧判据，未验桥 | `L007` §5 |
| 覆盖率矩阵已把该项列为 **#1 未覆盖** | `测试覆盖率矩阵.md` §八 |

⇒ **桥若再次 fail-open，当前没有任何判据能发现。**

## 前置事实（本轮实读）

| 项 | 值 |
|---|---|
| 桥文件 | `02-backend-node/src_restored/core/collect-bridge.js`（187 行） |
| 业务判据 | `:85-87` `okBusiness(r) { return r.ok === true && r.json?.code === 0; }` |
| 导出 | `shouldCollect` `acquireLock` `releaseLock` `reportResult` `bridgeEnabled` |
| `reportResult` 返回 | `{ ...r, ok }`，其中 `ok = okBusiness(r)`（`:175,186`） |
| Node 运行条件 | ✅ `node_modules` 已就绪（265 包，`npm ci` 已完成） |
| Go 服务 | 8888（含 F1-C1/C2/C8/C9 全部修复） |
| MariaDB / Redis | 13306 / 16379 |

## 规格

### (a) 必须**真实调用**桥，不得静态读源码

直接 `import` 产物内的 `collect-bridge.js`，让它真的对 Go 发 HTTP。

### (b) 断言矩阵（核心）

| # | 用例 | 桥的输入 | 期望 |
|---|---|---|---|
| **B1** | `reportResult` + **业务成功** | 合法归集（Go 返回 `code=0`） | `ok === true` |
| **B2** | ★ `reportResult` + **业务失败** | `amount = -5`（F1-C8 拒绝） | **`ok === false`** |
| **B3** | ★ `reportResult` + **业务失败** | `to_address` 不符（F1-C9 拒绝） | **`ok === false`** |
| **B4** | `reportResult` + **词表外 chain** | `chain = sol` | **`ok === false`** |
| **B5** | `shouldCollect` + 钱包 `progress=0` | 未占用 | `true` |
| **B6** | ★ `shouldCollect` + 钱包 `progress=1` | 已被潜客占用 | **`false`**（不双重归集） |
| **B7** | ★ `acquireLock` 后 `progress` 应为 1 | — | 返回 `true` 且 DB `progress=1` |
| **B8** | ★ `acquireLock` **冲突**（已占用） | 再占一次 | **`false`**（409 语义） |

★ **B2/B3/B4 是本卡的核心**：它们直接证明「Go 说失败 ⇒ 桥说失败」，即 **fail-closed**。

### (c) 反例对照（防假绿）

必须**同时**证明：**若只看 HTTP 状态，上述用例会误判为成功**。
即断言 `r.ok === true`（HTTP 200）而 `r.json.code !== 0` ——
**这正是 P0-3 的逃逸形态**。若不体现该对照，本卡的证据不完整。

### (d) 必须真实改 DB 状态并还原

`shouldCollect` / `acquireLock` 依赖 `wallet.progress`，须：
- 用 SQL 设置 `progress` 前置状态；
- 用例后**还原**（避免污染后续测试）。

### (e) 不得修改任何产物

纯验证卡。`forbidden_paths` 含全部产物代码。

## ★ 判据先于实现（判据 9）

本卡即「先写判据」本身（`verify_f1c10_bridge_e2e.mjs`）。

**前置断言（P-5）**：
1. Go 服务就绪（`/health` 200）；
2. `bridgeEnabled()` 为 true（否则桥会短路返回，断言无意义）；
3. **量尺有效性**：先证明「业务成功用例能返回 `ok=true`」——
   否则「`ok=false`」可能因为环境坏，而不是因为桥判对了。

## 不在范围

- 不修任何缺陷（若发现缺陷 ⇒ 登记上报 + 升级 Owner）
- 不测 `collect-task.js` / 确认链（W2-C6 范围）
- 不做真机 / 真链

## 证据要求

- `verify_f1c10_bridge_e2e.mjs` 真实退出码
- **B1–B8 逐条真实输出**（含桥返回的 `ok`、HTTP status、Go 的 `code`、msg）
- ★ **反例对照的原始证据**：展示"HTTP 200 但 code != 0" ⇒ 证明只用 `r.ok` 会 fail-open
- `collect-bridge.js` 的 sha256（本卡未改它，作基线登记）
- ★ **明确声明**：本卡验证的是**桥与 Go 的契约一致性**，**不是**链上归集正确性

## 停靠点

1. 若发现桥**确实 fail-open**（`ok=true` 而 `code!=0`）⇒ **立即停下升级 Owner**
   （属新 P0/P1，与 P0-3 同级）
2. 若 `bridgeEnabled()` 读取的环境变量与预期不符 ⇒ 停下确认配置语义
3. 若需修改产物才能让桥工作 ⇒ **停下升级**（本卡为纯验证卡）
