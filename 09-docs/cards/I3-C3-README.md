---
id: I3-C3
mode: 实施
wave: 二期-1
depends: []
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R1
定档理由: 纯新增文档，无代码改动 ⇒ R1（文件存在性 + 小节存在性可机械判定）
来源: 原审核报告 §五 第 5 层 5.8（未完成）+ V0 裁决 D-2（sweeper 规程）
base: []
allowed_paths:
  - README.md
  - 02-backend-node\README.md
  - 07-db\README.md
  - 08-infra\README.md
forbidden_paths:
  - "09-docs\\spec\\contracts.md"
  - "全部代码文件"
  - "10-sweeper\\README.md（归 F1-C7）"
  - "_manifest.sha256"
verify:
  - README.md 存在且非空
  - 02-backend-node/README.md 存在且非空
  - 07-db/README.md 存在且非空
  - 08-infra/README.md 存在且非空
  - grep -c '8888' README.md      # 须 ≥1（端口表）
  - grep -c '只读' README.md       # 须 ≥1（硬约束）
packages: {}
---

# I3-C3 [R1] 根 `README.md` 与模块 README

## 目标

让**新接手者**能在不看聊天记录的情况下理解项目。

## 规格（内容要求）

### 根 `README.md` 至少含

1. **项目定位**（一句话）
2. **11 个模块的一句话职责**
3. ★ **硬约束清单**：
   - `05-ios/**` 的 `.js`/`.dylib` 是**载荷本体，只读**（改则失效）
   - `E:\潜客\**`、`E:\ios漏洞\ios15-17版本漏洞\**`、`E:\IOSusdt\**` **只读**
   - 必须保留：隐蔽路径 `/mgr-admin-8bcde2021d98`、渠道码 `1DECX7UIQIB`+2 位、
     salt `cecd08aa6ff548c2`
4. ★ **端口表**：Go **8888** / Node **3000** / MariaDB **13306** / Redis **16379** / Mongo **27018**
   （并注明 vite dev 也占 8888）
5. ★ **工具位置**（**都不在 PATH**）：
   - go → `E:\ios漏洞\_integration\_fix_work\_toolchain\go\bin\go.exe`
   - node → `E:\CTF\runtime\node\node.exe`
   - python → 在 PATH
6. ★ **当前交付状态**（**必须如实**）：
   - 一期：iOS 链**不通**（`chain-router.js` 已按 `V0` **D-1** 降二期）
   - 一期不通项须**显式列出**，不得含糊
7. **阅读顺序**（指向 `09-docs/INDEX.md`）

### 模块 README

`02` / `07` / `08` 各一份，说明该模块职责、关键文件、与本项目其他模块的关系。

## ★ 硬性禁止

★ **不得写入任何凭据明文** —— 否则本文件自身成为泄漏点
（与契约本 §变更纪律 3、「定义检测模式的文档在产物内」同类自指，**P-4**）。

## 证据要求

- 4 份 README 的实际内容
- 各 grep 断言的**真实输出**
- ★ 交付状态章节的**事实来源**（须指向具体卡片或裁决编号）

## 停靠点

1. 若"当前交付状态"无法确定 ⇒ 停下升级（不得写含糊表述）
2. 若需改 `10-sweeper/README.md` ⇒ 那是 `F1-C7`，本卡不动
