---
id: F1-C4
mode: 实施
wave: 1
depends: []
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R2
定档理由: |
  触 02-backend-node/ecosystem.config.cjs —— 调度《真高危路径》表明列
  「实例数（影响并发归集）」属真高危。
  但本卡【只改默认值语义，不改并发模型】，且缺陷仅在"漏配 WORKERS"时触发，
  实际风险低于资金口径类 ⇒ 按 R2。
  门禁强度自知：本卡 verify 是【配置一致性断言】，**不是**运行时并发验证（见「证据要求」遗留）。
来源: 09-docs/reports/全量审核报告_独立复核版.md §三 P1-C（★ 该节修正了原报告的措辞）
base:
  - path: 02-backend-node\ecosystem.config.cjs
    sha256: e8420bf91ac9a11b3f1ca635276b01a97ada16dc11160d7f4f0058ada4219f9f
    bytes: 554
    eol: LF
  - path: 02-backend-node\src_restored\app.js
    sha256: db22eac83a506c733328557c3a5b9e633bb5bf2066c3946b51aa7e1eb7894492
    bytes: 10060
    eol: LF
    note: ★ 本卡【只读】app.js；若 I1-C2 已先行，此值须重新取值
  - path: 02-backend-node\config\index.js
    sha256: 需调度现场重取
    bytes: 需调度现场重取
    eol: LF
allowed_paths:
  - 02-backend-node\ecosystem.config.cjs
  - E:\ios漏洞\_integration\_fix_work\verify_f1c4_workers.mjs
forbidden_paths:
  - "09-docs\\spec\\contracts.md（契约本，只读）"
  - "02-backend-node\\src_restored\\app.js（★ 只读 —— 见规格 (b)，改它须先裁决）"
  - "02-backend-node\\config\\index.js（★ 只读 —— 见规格 (c)，改它须先裁决）"
  - "02-backend-node\\src\\**（扁平版，P-8）"
  - "02-backend-node\\src_restored\\schedules\\**（归集调度属 B 线）"
  - "01-backend-go/**、05-ios/**、06-android/**"
  - "_manifest.sha256"
verify:
  - node _fix_work\verify_f1c4_workers.mjs               # ①动前：须【红】，退出码 != 0，留证
  - node _fix_work\verify_f1c4_workers.mjs               # ②动后：须【绿】，退出码 0
  - node --check 02-backend-node/ecosystem.config.cjs    # 退出码 0
packages: {}
---

# F1-C4 [R2] `WORKERS` 默认值语义冲突 → 漏配即 N× 并发归集

## 目标

消除「`WORKERS` 未设时，PM2 起 N 个 worker 而 app 认为只有 1 个 ⇒ 每个 worker 都注册定时任务 ⇒ N× 重复归集」。

## 缺陷事实（本轮实读）—— ★ 本卡修正了原报告的措辞

| 位置 | 现状 |
|---|---|
| `ecosystem.config.cjs:5` | `instances: parseInt(process.env.WORKERS) \|\| 'max'` |
| `app.js:195` | `const totalWorkers = parseInt(process.env.WORKERS \|\| '1')` |
| `app.js:200` | `if (totalWorkers > 1 && task.instanceOnly !== instanceId) continue` |
| `config/index.js:15` | `workers: parseInt(process.env.WORKERS \|\| '0')` |
| `.env.example` | **`WORKERS=2` 已显式设置** |

★ **修正**：原审核报告 P1-3 称「未设 `WORKERS` → **必然** N× 并发」。复核后**该措辞不准确** ——
标准部署下 `.env.example` 已设 `WORKERS=2`，且两处读**同一个变量** ⇒
**配置正确时二者一致、守卫生效**。

**真实缺陷**：三处的**默认值语义互相矛盾**：

| 位置 | 未设 `WORKERS` 时 | 语义 |
|---|---|---|
| `ecosystem.config.cjs` | `'max'`（= CPU 核数） | 多实例 |
| `app.js` | `1` | 误以为单实例 ⇒ `totalWorkers > 1` 为**假** ⇒ **跳过 `instanceOnly` 守卫** |
| `config/index.js` | `0` | 又一种语义 |

⇒ **漏配即 N× 重复归集**。是**配置未设时的失败模式**，不是"配置正确也坏"。

## 规格

### (a) 让 `instances` 与 `app.js` 的 `totalWorkers` 同源

| 做法 | 内容 | 评价 |
|---|---|---|
| **(a1) 统一默认值为 `1`** | `ecosystem.config.cjs` 改为 `parseInt(process.env.WORKERS \|\| '1')` | ★ **推荐**：最小改动、语义一致、漏配时退化为单实例（**安全侧**） |
| (a2) 让 app 从 PM2 推导实例数 | 用 `NODE_APP_INSTANCE` / `instances` 推导 | 改动面更大，依赖 PM2 注入行为 |

执行者**二选一并说明理由**。

### (b) ★ 本卡不改 `app.js`

原报告 P1-3 的建议涉及 `app.js`。但 `app.js:195` 的 `|| '1'` **本身是安全的默认值**
（宁可少注册任务，不可重复注册）。**真正的坏值在 `ecosystem.config.cjs` 的 `'max'`。**
⇒ 只改一处即可闭合；改 `app.js` 属扩大范围，**须先裁决**。

### (c) `config/index.js` 的 `'0'`

该值**本卡不改**。执行者须**核实其消费者并写进证据**；
若发现它也参与归集守卫 ⇒ **停下升级**。

## ★ 判据先于实现（判据 9）

| # | 断言 | 红态（改前） |
|---|---|---|
| R1 | `ecosystem.config.cjs` 的 `instances` 默认值 === `app.js` 的 `totalWorkers` 默认值 | **`'max'` ≠ `'1'`** ⇒ 红 |
| R2 | 未设 `WORKERS` 时两处推导出的实例数**相等** | 不等 ⇒ 红 |
| R3 | 设 `WORKERS=2` 时，两处均为 `2` | 绿（**防改过头**） |
| R4 | `node --check ecosystem.config.cjs` 通过 | 绿 |

★ **R3 是防改过头用例**：显式配置的场景**必须**仍然正确。

★ **量尺前置断言（P-5）**：R1 必须在**改前**先跑出**红**（证明判据有鉴别力）。

## 不在范围

- 不改 `app.js`（见 (b)）
- 不改 `config/index.js`（见 (c)）
- **不做真实 PM2 多实例压测**（见「证据要求」遗留）

## 证据要求

- `verify_f1c4_workers.mjs` 改前红 / 改后绿两次真实退出码
- 三处默认值的**逐处引用**（文件:行号 + 原文）
- `config/index.js` 的 `workers` **消费者核实结论**
- `ecosystem.config.cjs` 改前 / 改后 sha256
- ★ **明确声明未覆盖场景**：本卡**未**在真实 PM2 cluster 下验证实例数与任务注册数的关系
  → 该验证列入 `I2-C2` 覆盖率矩阵的「未覆盖」格

## 停靠点

1. 若 `config/index.js` 的 `workers` 也参与归集守卫 ⇒ **停下升级**
2. 若执行者认为必须同时改 `app.js` ⇒ **停下升级**（扩大范围）
