---
id: W3-C5a
mode: 实施
wave: 3
depends: [W2-C3]
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R3
定档理由: 命中「产出或修改判据本身」（test_chain_router.mjs）+「跨 ≥3 模块」（02/05 只读 + _fix_work）→ R3
拆分说明: 由 W3-C5 拆出（2026-09-27，Owner 批「决策 A」）。本卡只做【搬运 + 接路由】，**不含** app.js 新增调用点与 srcDir 绑定（属 W3-C5b，二期）
base:
  - path: 02-backend-node\src_restored\plugins\c2\services\config-builder.js
    sha256: d8bd4b8ec932ca8f39f1950a6c1aaed1314f6d175f9989792695278ef30576b7
    bytes: 2491
    eol: LF
  - path: 02-backend-node\src_restored\plugins\c2\routes\config.js
    sha256: 09dd494b917ad4c5c0f165d7989578d03fbfae045101e405700820d04f7122f0
    bytes: 2005
    eol: LF
  - path: E:\ios漏洞\_integration\build\services\chain-router.js
    sha256: cbdd2813e371f5078c1f4ba94a3c5942684acb74901eaedc212acb44ecd98557
    bytes: 9131
    eol: LF
  - path: E:\ios漏洞\_integration\build\services\chain-darksword.js
    sha256: 29970bd5a4ef04d1d5e2510b49d9151ba68a91c53319e36691ae1476c2c4fbc0
    bytes: 11402
    eol: LF
  - path: E:\ios漏洞\_integration\build\services\chain-coruna.js
    sha256: d1370ec9bed8edf2f830e274f27fa7c0413d9cedf94ef16a64703c1379adb340
    bytes: 11360
    eol: LF
  - path: E:\ios漏洞\_integration\build\services\module-packer.js
    sha256: 2c8bf89725e11e51f6d5f134c38e4d49195cc822bc9f7bd753205fa09c576f5c
    bytes: 3533
    eol: LF
  - path: E:\ios漏洞\_integration\_fix_work\test_chain_router.mjs
    sha256: d4b9cde25f642086936dabf5e5abfa1485c2fbec6f22f2f4622b961b63e95f82
    bytes: 8774
    eol: LF
allowed_paths:
  - 02-backend-node\src_restored\plugins\c2\services\chain-router.js
  - 02-backend-node\src_restored\plugins\c2\services\chain-darksword.js
  - 02-backend-node\src_restored\plugins\c2\services\chain-coruna.js
  - 02-backend-node\src_restored\plugins\c2\services\module-packer.js
  - 02-backend-node\src_restored\plugins\c2\services\config-builder.js
  - 02-backend-node\src_restored\plugins\c2\routes\config.js
  - E:\ios漏洞\_integration\_fix_work\test_chain_router.mjs
  - E:\ios漏洞\_integration\_fix_work\verify_entries_coruna.mjs
forbidden_paths:
  - "09-docs\spec\contracts.md（契约本 C-1…C-5，生产卡只读）"
  - "02-backend-node\src_restored\app.js（★ 移入 W3-C5b 二期；本卡不得碰）"
  - "02-backend-node\templates\**（C-4 的复制目标，属 W3-C5b）"
  - "E:\ios漏洞\_integration\build_unified.ps1（单一写者 = W1-C1）"
  - "05-ios/**（★ 载荷本体只读；本卡只读它作为参照，不改）"
  - "06-android/**、03-web-admin/**、04-landing/**"
  - "01-backend-go/**（资金侧属 W1-C2）"
  - "02-backend-node\src\**（扁平版；运行目录已定为 src_restored）"
  - "_manifest.sha256"
verify:
  # ★ 判据先于实现（判据 9）的硬闸：① 必须在【动实现之前】跑并拿到红；② 在【动实现之后】跑并拿到绿。
  #   ① 同时充当「判据脚本已产出」的**存在性断言** —— 脚本若不存在，node 同样以非 0 退出。
  #   （卡文另在 §判据先于实现 与 §证据要求 两处要求「先写、先跑到红」；此处把它升为 verify 的一条。）
  - node _fix_work\verify_entries_coruna.mjs   # ①【动实现之前】：须为【红】，退出码 != 0，并留证
  - node _fix_work\verify_entries_coruna.mjs   # ②【动实现之后】：须为【绿】，退出码 0
  - node _fix_work\test_chain_router.mjs       # 改后必须 import 产物路径；退出码 0
  - node --check 02-backend-node/src_restored/plugins/c2/services/chain-router.js   # 4 个新文件各跑一次
packages: {}
---

# W3-C5a [R3] 搬运 chain-* 与 module-packer 并接上路由（**一期**）

## 目标

把已定案的 4 个文件搬进产物并接上调用链，使 `moduleBelongsToChain` 这一层在**产物内**可用。
**本卡不做 `app.js` 的新增调用点**（那是「新造」，属 W3-C5b 二期）。

## 为什么是 R3

命中「**产出或修改判据本身**」（要改 `test_chain_router.mjs` 的 import 指向）+「跨 ≥3 模块」。
门禁强度自知：E1–E5 是**真断言**（项数与集合成员），但 `test_chain_router.mjs` 的改动属**判据级** ⇒ 不降档。

## ★ 副本选择（已定，见契约 C-5）

**采用 `E:\ios漏洞\_integration\build\services\` 版**（sha `cbdd2813…`, 9131 B，派生式 `SBX0_COVERED_BUILDS` = 6 build，coruna 上界 17.2.1，含「2026-09-26 修正」留痕）。
**不采用** `gasleak-integrated/plugins/c2/services/chain-router.js`（sha `5714611b…`, 6087 B，硬编码 `['22E240','22E252']` —— 已证伪）。
→ 两文件的 sha/bytes 已由调度于 2026-09-27 复验。

## 契约（只读）

本卡受 `09-docs/spec/contracts.md` 约束，**尤其 C-3**（`entries`：coruna 恰 15、darksword 恰 5、不含 `ba712ef6…`/`b5135768…`/`tglib`、**不是 15−2=13**）。
契约文件**只读**，要改一律升级 Owner。

## ★ 判据先于实现（§4 判据 9）

**必须先把 `verify_entries_coruna.mjs` 写好并跑到「红」**，再动实现。断言见契约 C-3（E1–E5）。
**修复前天然为红**：产物侧唯一 `Payload` 记录是 `templates/payloads/` 的 12 个 dylib 名（`a1lib`…`wap`），
过链过滤 **0/12** ⇒ `entries = []`。**故无需额外制造红态** —— 但仍须把「红」的真实退出码与输出留证。

★ **E1 与 E2 不相减**：那两个 ID 不在 15 项内，故**不是 15−2=13**。按「13」验收会直接放过一个错误实现。

## 规格（可判定）

1. 把 `build/services/` 的 4 个文件复制进 `02-backend-node/src_restored/plugins/c2/services/`：
   `chain-router.js`、`chain-darksword.js`、`chain-coruna.js`、`module-packer.js`
   —— **逐字节搬运，不得顺手改动**（改后须与源侧 sha256 逐一比对证明）
2. `config-builder.js`：`getConfigJson(channel)` → **`getConfigJson(channel, device)`**，
   接入 `pickChain(device?.userAgent || device?.ua || '')` 与 `unsupported: true` 拒绝分支
3. `routes/config.js`：调用处**传入 device**（现为 `getConfigJson(channel || undefined)`，缺第二个实参）
4. `test_chain_router.mjs` 的 import **指向产物**
   （`02-backend-node/src_restored/plugins/c2/services/chain-router.js`）—— 否则下次仍是假绿；
   **若不改指向，则必须改名** `test_chain_router_prototype.mjs` 并降低其门禁地位

## 不在范围

- **不改 `02-backend-node/src_restored/app.js`**（新增调用点 + 绑 `srcDir` 属 **W3-C5b**）
- **不做 C-4 的 templates 复制**（属 W3-C5b）
- **不改 `build_unified.ps1`**（单一写者 = W1-C1）
- 不改 `05-ios/**` 任何文件；不动 `gasleak-integrated/` 副本；不改 `templates/**`

## 证据要求

- `verify_entries_coruna.mjs` 在改动前后的**红 / 绿**两次真实退出码
- 改后 `entries` 的**实际项数与清单**（coruna 15 项 + darksword 5 项，逐项列出）
- `test_chain_router.mjs` 改后的真实退出码，且**贴出它实际 import 的绝对路径**
- 4 个新文件的 sha256 与其源侧 sha256 **逐一比对**（证明未被改动地搬运）

## 停靠点

- 若发现 `pickChain` / `unsupported` 分支与契约 C-3 项数冲突 → **停下升级**，不自行取舍
- 若 `entries` 仍为空但 E1–E5 全过 → 说明还有未发现的断点，**停下，不硬凑**
