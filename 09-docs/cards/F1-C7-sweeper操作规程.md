---
id: F1-C7
mode: 文档
wave: 1
depends: []
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R1
定档理由: |
  本卡**不改任何代码** —— Owner 已裁 `D-2`：10-sweeper 保持离线、不接入互斥。
  本卡只把该裁决落成**操作规程文档**（`10-sweeper/README.md`），
  属纯文档、判据可机械判定（文件存在 + 含指定小节）⇒ R1。
来源: 09-docs/cards/V0-本轮裁决留痕.md 裁决 D-2
base: []
allowed_paths:
  - 10-sweeper\README.md
forbidden_paths:
  - "09-docs\\spec\\contracts.md（契约本，只读）"
  - "10-sweeper\\wsweep\\**（★ 代码不动 —— D-2 已裁不接入互斥）"
  - "01-backend-go/**、02-backend-node/**、05-ios/**、06-android/**"
  - "_manifest.sha256"
verify:
  - 10-sweeper/README.md 存在且非空
  - grep -c '广播前' 10-sweeper/README.md          # 须 ≥1（操作规程须含前置条件）
  - grep -c '不存在技术互斥' 10-sweeper/README.md    # 须 ≥1（残余风险须显式登记）
  - grep -c '人工' 10-sweeper/README.md             # 须 ≥1
packages: {}
---

# F1-C7 [R1] `10-sweeper` 操作规程与残余风险登记

## 目标

把 **`V0` 裁决 D-2**（保持离线、不接入互斥）落成**可执行的规程文档**，
使"三条归集路径无技术互斥"这一残余风险**可见、可依赖人工兜底**。

## 背景（本轮实读）

- `10-sweeper` 全模块 grep `collect-lock|collect-release|acquireLock` → **零命中**
- ⇒ `--broadcast` 可**真广播**，与 gasleak 自动调度、潜客 `Sk()` **无任何互斥耦合**
- 三条路径并行 ⇒ **可能对同一地址重复归集**

## 规格

`10-sweeper/README.md` 至少含以下小节：

### (a) 模块定位

说明它是**离线命令行工具**（9 链），与 `01`/`02` 的自动路径**机制不同**。

### (b) ★ 操作规程：广播前的前置条件

必须写明：

> 执行 `--broadcast` 前，**必须确认**：
> 1. 目标地址**不在** gasleak 的自动归集队列中（`DerivedAddress.collectStatus != 'collecting'`）；
> 2. 目标地址**不在**潜客 `Sk()` 的执行中（`wallet.progress != 1`）；
> 3. 若无法确认 ⇒ **不得广播**。

★ 这是 `D-2` 的**代价兜底** —— 既然不做技术互斥，就必须把规程写死。

### (c) ★ 残余风险显式登记

必须写明：

> **本模块与另两条归集路径不存在技术互斥。**
> 重复归集的防护**完全依赖上述操作规程**。
> **触发复审条件**：若本模块被改为**自动/高频**调用，本裁决失效，须重裁。

### (d) 免责与边界

写明：**不修改载荷本体**、**原始素材只读**等硬约束（与项目总约束一致）。

## 不在范围

- ★ **不改任何代码**（`D-2` 已裁不接入互斥）
- 不新增互斥逻辑、不改 `sweep.py` / `cli.py`

## 证据要求

- `10-sweeper/README.md` 的实际内容
- 三条 grep 断言的**真实输出**
- ★ 明确声明：本卡**未**改动任何 `.py` 文件（附 `git`-less 的 sha256 对照或文件清单）

## 停靠点

1. 若执行者认为规程不足以防重复归集 ⇒ **登记上报 + 建议重开 `D-2`**，
   **不得自行加互斥代码**
