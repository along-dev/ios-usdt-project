---
id: W3-C5b
mode: 实施
wave: 二期
depends: [W3-C5a, W1-C1]
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R3
定档理由: 命中「真高危路径」（app.js 是归集/投递链路的运行时入口）+「产出或修改判据本身」+「跨 ≥3 模块」→ R3
拆分说明: |
  由 W3-C5 拆出（2026-09-27，Owner 批「决策 A」）。
  ★ id 重命名登记（判据 11）：原始记录写作 `W3-C5a′`，落盘为 **`W3-C5b`** ——
  避免文件名与 id 中出现 prime 字符（`′`）带来的转义风险。语义未变。
期别: **二期** —— 本卡是「**新造**」，受一期「只整合、不新造」铁律约束（Owner 批「决策 A」）。
base:
  - path: 02-backend-node\src_restored\app.js
    sha256: db22eac83a506c733328557c3a5b9e633bb5bf2066c3946b51aa7e1eb7894492
    bytes: 10060
    eol: LF
  - path: E:\ios漏洞\_integration\build_unified.ps1
    sha256: 76ee6e1166c0b1d5c9be8963b3ff1d9dcddefcab0e86907f9960de2b46df48ee
    bytes: 35261
    eol: LF
    # ★★ 2026-09-27 `depends` 补 `W1-C1`（独立审核者 B 指出，见台账 L024 §F4）：
    #    本卡的单一写者冲突**此前未在卡面表达** —— 契约 C-4 明写该文件的改动「必须排在 W1-C1 之后，由同一写者承接」，
    #    而本卡原先 `depends: [W3-C5a]`、`base` 仍是 **W1-C1 改前**的 `76ee6e11…`。
    #    ⇒ 若按原样派发，会**静默回退 W1-C1 的 3 值登记**（正是"下次重新引入"的同一失效模式）。
    #    ★ **本行的 base 只是「改前」快照**；**派发前必须重取**（须在 W1-C1 采纳之后）。
    #      —— 与 `W1-C9` / `W1-C10` 的 `base: []` + `base_待取说明` 同一手法。
  - path: E:\ios漏洞\_integration\build\services\chain-coruna.js
    sha256: d1370ec9bed8edf2f830e274f27fa7c0413d9cedf94ef16a64703c1379adb340
    bytes: 11360
    eol: LF
  - path: E:\ios漏洞\_integration\build\services\chain-darksword.js
    sha256: 29970bd5a4ef04d1d5e2510b49d9151ba68a91c53319e36691ae1476c2c4fbc0
    bytes: 11402
    eol: LF
allowed_paths:
  - 02-backend-node\src_restored\app.js
  - 02-backend-node\templates\coruna\**
  - 02-backend-node\templates\darksword\**
  # ★ 2026-09-27 修正（C-4(b) 的「第二处」）：原稿只允许 02 侧，却在 forbidden 里禁掉 `04-landing/**`，
  #   与正文「构建脚本同源产出【两处】、禁止手工只改其一」**自相矛盾** ⇒ 执行者按卡面只能产出一处、verify 还全绿。
  #   现补入第二处（独立审核者指出后修正）。
  - 04-landing\ios-templates\coruna\**
  - 04-landing\ios-templates\darksword\**
  - E:\ios漏洞\_integration\build_unified.ps1
forbidden_paths:
  - "09-docs\spec\contracts.md（契约本 C-1…C-5，生产卡只读）"
  - "05-ios/**（★ 载荷本体只读；本卡只【读】它作 srcDir 来源）"
  - "02-backend-node\src_restored\plugins\c2\services\chain-*.js（属 W3-C5a，本卡不改）"
  - "02-backend-node\src\**（扁平版）"
  - "06-android/**、03-web-admin/**"
  - "04-landing\assets\**、04-landing\runtime\**、04-landing\templates\**（第二处 templates 已列 allowed_paths，见上）"
  - "01-backend-go/**"
  - "_manifest.sha256"
verify:
  # ★★ 第 3 条【未补齐】—— **未补齐前本卡不得判定为完成**（「待定」不等于「可跳过」）。
  #    缺此条时，本卡仅剩两条静态检查 ⇒ **没有任何一条 verify 能证明「目标达成」**（空缺绿）。
  - node --check 02-backend-node/src_restored/app.js                                        # 退出码 0
  - node _fix_work\verify_entries_coruna.mjs                                                # E1–E5 仍须全过；退出码 0（★ 该脚本由 W3-C5a 产出）
  - ★【未补齐 · 开工前必修】`entries` 在**真实运行实例**上非空的端到端断言                  # 见「停靠点」
packages: {}
---

# W3-C5b [R3] 生产调用点 + `srcDir` 绑定 + templates 同源产出（**二期**）

## 目标

让 `entries` 在**真实运行路径**上非空：给 `app.js` 新增调用点，调 `syncCorunaPayloads` / `syncDarkswordPayloads`，
并**绑定 `srcDir`**。

## 为什么这是「新造」（Owner 批「决策 A」的判据）

实测：`syncCorunaPayloads` / `syncDarkswordPayloads` 的签名是 `syncXxxPayloads(srcDir, storageRoot, ...)`，
`srcDir` 是**纯入参、全源树无任何地方为其提供值**（实测全源树仅 4 处命中，**全是定义 / JSDoc**；
`app.js` **零调用**）。
⇒ 新增调用点 = **新造一条生产链路**，不是整合已有能力。故**一期不做**。

**一期不接此线的代价（如实登记）**：**iOS 链在一期不可用**（设备拿到空配置）。
该事实须在 `需求文档.md` §3.1 一期验收表与 §5.2.5 显式标注。

## 契约（只读，尤其 C-4）

**C-4 已裁为 (b)**：`srcDir` 指向「**复制进 `02-backend-node/templates/`** 的副本」（**只复制不移动**），
并在构建脚本中**同源产出** —— 与 B2「templates 两处都留」同做法。
**代价（已登记）**：产生重复副本，与 B2 同类的漂移风险 ⇒ 必须由构建脚本同源产出两处，**禁止手工只改其一**。

## 规格（待细化，见「停靠点」）

1. `app.js`：新增调用点调 `syncCorunaPayloads(srcDir, storageRoot, ...)` / `syncDarkswordPayloads(...)`，
   并**绑定 `srcDir`**：
   - coruna `srcDir` → `<产物>/05-ios/coruna`（**只读**）→ 经 C-4(b) 复制到 `02-backend-node/templates/coruna`
   - darksword `srcDir` → `<产物>/05-ios/darksword` → 复制到 `02-backend-node/templates/darksword`
2. `build_unified.ps1`：新增「把 coruna/darksword 模块**同时**产出到 `02-backend-node/templates/`」
   —— 与 B2 的 templates 双产出同源

## ★ 共享文件冲突（已登记，须先解）

`E:\ios漏洞\_integration\build_unified.ps1` 的**单一写者是卡 W1-C1**（改其脱敏模式表）。
⇒ **本卡必须在 W1-C1 完成之后开工**，且改后须指定**完整性核查人**并复跑 W1-C1 的两条 verify。
**未解之前不得开工。**

## 停靠点（★ 开工前必须补的）

- **verify 第 3 条待定**：需要一条「`entries` 在真实运行实例上非空」的端到端断言。
  它必须先于实现成形（判据 9），且不得照着实现写。
  ⇒ 开工前由调度组织一次**判据设计**（可能需起 Mongo 27018 + Node 3000，走取数协议确认端口归属）。
- 若发现绑 `srcDir` 后 `syncCorunaPayloads` 需要**写 `05-ios/**`**（而非只读）→ **停下升级 Owner**：
  那会违反「载荷本体不可改」硬约束。
- 若发现需要**新增集合 / 新写 `templates/`** 之外的位置 → 停下升级。

## 不在范围

- 不改 `chain-*.js` / `module-packer.js`（属 W3-C5a）
- 不改 `05-ios/**` 任何文件
- 不为 `btc` / 其它链新增能力
- 不改 `_manifest.sha256`

## 证据要求（预登记）

- `node --check app.js` 的真实退出码
- `verify_entries_coruna.mjs` 的真实退出码
- 第 3 条端到端断言的红/绿两次真实退出码 + 实例内容指纹（取数协议）
- `build_unified.ps1` 的 **BOM 前三字节**（hex）+ PowerShell 语法解析输出（P-6）
- 复制到 `templates/` 的模块与 `05-ios/` 源的 sha256 **一一比对**
- ★ **两处 templates 的一致性比对**（C-4(b) 的核心风险 = 只改一处造成漂移）：
  `02-backend-node\templates\{coruna,darksword}` ↔ `04-landing\ios-templates\{coruna,darksword}`，
  逐文件 md5/sha256 比对并**报告两侧文件数**
  （2026-09-27 调度实测基线：两处各 **98 文件**，同构）
