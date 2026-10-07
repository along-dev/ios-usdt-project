# T61 —— `IOS源码1` → USDT **移植 G3**：`schedules/balance-refresh.js` ＋ `index.js` 注册

> **卡**：T61 ｜ **来源**：架构线需求件（`IOS源码1补入-需求件_20261005.md`）· ★★ **Owner 裁定（`L073`）：派 G3**
> **档**：**R2** ｜ **执行**：**待派** ｜ **收口/提交**：总调度第四任
> **状态**：**已立卡、待派**（★ Owner「按建议裁决」＋「继续，立卡派单」）｜ **日期**：2026-10-05

---

## 一 · 任务定义

| 项 | 值 |
|---|---|
| **基准** | `E:\IOS源码1\server\src\schedules\balance-refresh.ts`（★ **非 git 仓库** ⇒ **按 `sha256` 取件**，⛔ 不按文件名/日期） |
| **目标** | `E:\USDT项目\02-backend-node\src_restored\schedules\balance-refresh.js`（**新增**） |
| **动作** | ★ **`.ts` → `.js` <ins>保义改写</ins>**（★ **非重写**） |
| **注册点** | `src_restored/schedules/index.js` 补 `import { balanceRefresh } from './balance-refresh.js';` ＋ 把 **`balanceRefresh`** 加入 `tasks` 数组（★ 与现有 **14** 条注册**同形**） |

★ **依赖闭合性（架构线实测）**：`balance-refresh` **0 缺失**（models／logger／tatum×4／类型）★ **且其 import <ins>不含 `auto-collect`</ins>** ⇒ 与 `T62` **不相交** ✓

## 二 · ★ 转换口径（**含先例锚** —— 本卡最可操作的一节）

**先例**：USDT 已从**同一基准**移过同族件 —— `schedules/balance-init.js`（**90 行**）← `balance-init.ts`（**112 行**）。
**逐行对照得到的既定转换法**：

| 规则 | 依据（先例） |
|---|---|
| ★ **`import type { … }` 整行<ins>删除</ins>**（⛔ **不得**转成运行时 import） | `balance-init.ts:2,9` 的两条 `import type` 在 `.js` 中**消失** |
| **运行时 import 原样保留** | `.ts:1,3-8` ↔ `.js:1-7` 逐条对应 |
| **类型标注／接口／`as` 断言<ins>删除</ins>** | 112 → 90 行 |
| ★ **中文注释 · 字符串字面量 · 数值常量 · 控制流<ins>一律保留</ins>** | 承 Owner 要求 |
| **`export const x: ScheduleTask = {…}` ⇒ `export const x = {…}`** | 同先例 |

★★ **一个必踩的坑**：`src_restored/schedules/types.js` 是**空壳**（内容只有 `export {};`）。
若把 `import type { ScheduleTask } from './types.js'` 误转成 `import { ScheduleTask } from './types.js'` ⇒ ★ **运行时 `SyntaxError: does not provide an export named 'ScheduleTask'`**。

## 三 · 范围

| 项 | 内容 |
|---|---|
| **改** | ★ **新增** `src_restored/schedules/balance-refresh.js` ＋ 改 `src_restored/schedules/index.js`（**仅注册那一处**） |
| ⛔ **不得** | **写 `src/`**（那是**未修改的上游基线快照** —— 自带 `README-NONAUTHORITATIVE.md`，`start:flat` 显式 `exit(1)`）· ⛔ 改 `05-ios/**` · ⛔ 改 `migration/**`／判据装置／`core/collect/**`（那是 `T62`）· ⛔ 改 `schedules/index.js` 的**其它注册** · ⛔ 改 USDT **既有 15 个独有文件** |
| ★ **停止条件** | 若发现**别的件**也在同一批缺 ⇒ **列出报总调度**，⛔ 不扩面 |

## 四 · 验收（★ 真退出码；取码不接管道）

| # | 断言 |
|---|---|
| **V1** | ★ **取件按 `sha256`**：★ 先落基准件 `sha256 ＋ bytes` 清单，**取件后<回读>复核** ✓ |
| **V2** | ★ **保义判据（<ins>逐文件</ins>）**：`.ts` vs `.js` 的 **中文注释条数 · 字符串字面量集合 · 数值常量集合**三者对照（⛔ **不只比行数**） |
| **V3** | ★★ **冒烟必须在<隔离端口>（如 `3100`）** ⇒ ⛔ **不得动共享 `3000`**（**当前 3000 有实例在跑**）⇒ 且**确认无 import 错误** |
| **V4** | ★ **类型名零残留**：`grep -n "^import" balance-refresh.js` ⇒ **无 `ScheduleTask`/`IDerivedAddress` 等类型名** ✓ |
| **V5** | ★ **注册可加载**：`node -e "import('./src_restored/schedules/index.js')"` 或等价 ⇒ **不抛** |
| **V6** | ★ **回滚方案**：记录**改前 `schedules/index.js` 的 `sha256`**；★ 本批 ＝ **纯新增 1 件 ＋ 改 1 注册** ⇒ 回滚 ＝ 删新件 ＋ 还原注册件 ✓ |

## 五 · 边界与停靠点

- ⛔ **不做 git 写操作**（提交权在总调度）· ★ node **不在 PATH** ⇒ 用 `E:\CTF\runtime\node\node.exe` · ★ 若写 `.ps1` ⇒ **须 UTF-8 BOM**（PS 5.1）。
- ★ **单线串行**（总量仅 1 新件 ＋ 1 注册）—— ★ 架构线 §九-10 的建议 ✓
- ★ 档 **R2**；★ ★ **派单须明写「复核方之间也串行」**（承 `L071 §五-4`）。
