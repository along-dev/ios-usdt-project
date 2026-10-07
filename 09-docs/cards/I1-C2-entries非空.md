---
id: I1-C2
mode: 实施
wave: 二期-2
depends: [I1-C1, F1-C4]
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R3
定档理由: |
  本卡是「entries 恒空」的**正面修复**，直接决定 iOS 投递链路是否可用
  —— 与 P0-1（静默丢账）同级：都是"看起来正常、实际链路不通"。
  契约 C-3 已冻结断言值 ⇒ 判据明确、可判定 ⇒ 有资格 R3。
  门禁强度自知：必须用【entries 实际项数 + 逐项清单】断言，
  不得只看 "sync 函数被调用了"。
  ★ 额外依赖 F1-C4：本卡在 app.js 新增受 instanceId 控制的写入点，
  须先修好 WORKERS 默认值语义，避免"在错的并发前提下新增写入点"（见卡 I1-C1 §并行说明）。
来源: 契约 C-3 / C-4 + 卡 W3-C5b（生产调用点与 srcDir 绑定）
base:
  - path: 02-backend-node\src_restored\app.js
    sha256: db22eac83a506c733328557c3a5b9e633bb5bf2066c3946b51aa7e1eb7894492
    bytes: 10060
    eol: LF
    note: ★ 若 F1-C4 已先改 ecosystem 但未改 app.js，此值不变；须由调度重取确认
  - path: 02-backend-node\src_restored\plugins\c2\services\chain-coruna.js
    sha256: d1370ec9bed8edf2f830e274f27fa7c0413d9cedf94ef16a64703c1379adb340
    bytes: 11360
    eol: LF
    note: 由 I1-C1 搬运产出；须与源侧 sha256 相同
  - path: 02-backend-node\src_restored\plugins\c2\services\chain-darksword.js
    sha256: 29970bd5a4ef04d1d5e2510b49d9151ba68a91c53319e36691ae1476c2c4fbc0
    bytes: 11402
    eol: LF
    note: 由 I1-C1 搬运产出；须与源侧 sha256 相同
allowed_paths:
  - 02-backend-node\src_restored\app.js
  - 02-backend-node\src_restored\plugins\c2\**      # 仅当发现该层还需小改（默认不动）
  - 02-backend-node\templates\**                   # ★ srcDir 副本产出（契约 C-4 (b)）
  - E:\ios漏洞\_integration\_fix_work\verify_entries_coruna.mjs
forbidden_paths:
  - "09-docs\\spec\\contracts.md（契约本，只读）"
  - "05-ios/**（★ 载荷本体，硬约束只读 —— 只【读】不写）"
  - "02-backend-node\\src\\**（扁平版，P-8）"
  - "02-backend-node\\ecosystem.config.cjs（属 F1-C4）"
  - "02-backend-node\\src_restored\\schedules\\**（归集调度属 B 线）"
  - "02-backend-node\\src_restored\\core\\collect*（归集，属 B 线）"
  - "01-backend-go/**、03-web-admin/**、04-landing/**、06-android/**"
  - "E:\\ios漏洞\\_integration\\build_unified.ps1（单一写者 = W1-C1）"
  - "_manifest.sha256"
verify:
  # ★ 判据先于实现：脚本【不存在】⇒ 第 1 条天然为红（无需额外制造红态）
  - node _fix_work\verify_entries_coruna.mjs     # ①动前：须【红】，退出码 != 0，留证
  - node _fix_work\verify_entries_coruna.mjs     # ②动后：须【绿】，退出码 0
  - node --check 02-backend-node/src_restored/app.js   # 退出码 0
packages: {}
---

# I1-C2 [R3] 产出 `entries` 并使其非空（**二期核心卡**）

## 目标

让 `entries` **在真实运行实例上非空**，且**逐项符合契约 C-3**。

## 为什么这张卡是「新造」（承接 `V0` 裁决 D-1）

`V0` 裁决 **D-1** 把 `chain-router.js` 接入降为二期，理由是
**在 `app.js` 新增调用点属"新造"**，违反一期"只整合、不新造"铁律。

**本卡就是那个"新造"的落地点。** 二期明确接受这个新造。

## 前置事实（本轮实读）

| 事实 | 位置 |
|---|---|
| `syncCorunaPayloads(srcDir, storageRoot, allStages, packMode)` | `_integration\build\services\chain-coruna.js:163` |
| `syncDarkswordPayloads(srcDir, storageRoot, base, include186, host, packMode)` | `_integration\build\services\chain-darksword.js:162` |
| 这两个函数在**产物内当前不存在** | 全仓 grep `syncCorunaPayloads\|syncDarkswordPayloads` → **零命中** |
| 模板素材位置 | `E:\ios漏洞\_integration\build\context\app\templates\`（含 `payloads/` 12 个 dylib、`exploit/`、`landing/`） |
| 产物模板位置 | `02-backend-node\templates\`（B2 已补入） |
| 启动时载荷注册 | `app.js` → `initPayloads()`（在 `instanceId === 0` 分支内调用） |

## 规格

### (a) 先写判据、先跑到红

`verify_entries_coruna.mjs`（放产物外，**P-4**）**必须先写**，且先跑到**红**。
断言**按契约 C-3 冻结值**：

| # | 断言（契约 C-3） |
|---|---|
| E1 | coruna `entries` **恰 15** |
| E2 | darksword `entries` **恰 5** |
| E3 | **不含** `ba712ef6…` |
| E4 | **不含** `b5135768…` |
| E5 | **不含** `tglib`（负例） |

★ **E1 不是 `15 − 2 = 13`**（契约 C-3 明确警告）：
`ba712ef6…`/`b5135768…` **不在**这 15 项内，两者交集为 **0**。
**按「13」验收会直接放过一个错误实现。**

★ **红态来源**（无需额外制造）：产物侧唯一 `Payload` 记录是
`templates/payloads/` 的 12 个 dylib 名（`a1lib`…`wap`），
过 `moduleBelongsToChain` 为 **0/12** ⇒ **`entries = []`** ⇒ 断言**天然为红**。

### (b) `srcDir` 按契约 C-4 **(b)** 产出

`srcDir` 指向**复制进 `02-backend-node/templates/`** 的副本（**只复制不移动**）。

★ **共享文件冲突（必须登记）**：契约 C-4 要求构建脚本**同源产出两处**，
而 `build_unified.ps1` 的单一写者是 **W1-C1**。
⇒ 本卡**若需改该脚本**，必须**排在 W1-C1 之后**，由**同一写者**承接，并指定完整性核查人。
**本卡默认不动该脚本**；若必须动 ⇒ **停下升级**（见停靠点 2）。

### (c) ★ 新增 `app.js` 调用点（本卡主体）

在 `app.js` 初始化段（参考现有 `instanceId === 0` 分支）加入
`syncCorunaPayloads` / `syncDarkswordPayloads` 调用：

1. **必须限定 `instanceId === 0`** —— 多 worker 下不得每个实例都同步（重复写入）；
2. `srcDir` 须指向**产物内**路径（`templates/` 副本），**不得**指向 `05-ios/`
   （契约 C-4 已裁 (b)：避免跨模块依赖只读素材）；
3. 同步失败的**错误处理必须显式**（不得静默吞）；
4. **不得**因为"让 entries 看起来有值"而伪造/补齐数据（**P-1** 形态）。

### (d) 不得改载荷本体

`05-ios/**` 的 `.js`/`.dylib` **只读**（硬约束）。
本卡**只读**它们（或读已复制到 `templates/` 的副本）来派生 `entries`，**不得写入**。

## ★ 判据先于实现（判据 9）

**绿态要求**：
- E1–E5 **全部通过**；
- ★ **并在证据中逐项列出** coruna 15 项 + darksword 5 项的**实际清单**；
- ★ 若 `entries` 仍为空但 E1–E5 全过 ⇒
  **说明还有未发现的断点，停下，不硬凑**（W3-C5a §129 原文要求）。

## 不在范围

- 不改 `build_unified.ps1`（除非 Owner 批准，见 (b)）
- 不改 `05-ios/**`（硬约束）
- 不改 `ecosystem.config.cjs`（属 `F1-C4`）
- 不改 `schedules/**` / `core/collect*`（B 线归集）
- **不做真实 iOS 设备投递验证**（需真机；`V0` 裁决 **D-4** 已登记为残余局限）
- 不改 `_manifest.sha256`

## 证据要求

- `verify_entries_coruna.mjs` **改前红 / 改后绿**两次真实退出码
- ★ `entries` 改后**实际项数与逐项清单**（coruna 15 + darksword 5）
- `app.js` 改前 / 改后 sha256 + diff
- `templates/` 副本的 sha256（证明与源同源）
- ★ **明确声明**：本卡**未**在真机验证投递成功（只验证 `entries` 非空）；
  真机验证已按 **D-4** 登记为残余局限

## 停靠点

1. 若 E1–E5 全过但 `entries` 仍为空 ⇒ **停下升级**（不硬凑）
2. 若需改 `build_unified.ps1` ⇒ **停下升级**（单一写者 W1-C1 + 脱敏门禁）
3. 若发现需写 `templates/` **之外**的新落点 ⇒ 停下升级（越出 allowed_paths）
4. 若 `syncCorunaPayloads` 需要 `srcDir` 指向 `05-ios/**` 才能工作 ⇒
   **停下升级**（与契约 C-4 裁决 (b) 冲突）
5. 若 `app.js` 的改动需要触碰 `initPayloads` 之外的**既有初始化顺序** ⇒
   停下升级（可能影响启动时序）
