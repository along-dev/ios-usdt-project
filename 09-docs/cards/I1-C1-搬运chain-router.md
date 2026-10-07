---
id: I1-C1
mode: 实施
wave: 二期-1
depends: []
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R3
定档理由: |
  命中「产出或修改判据本身」（本卡要改 test_chain_router.mjs 的 import 指向）
  +「跨 ≥3 模块」（src_restored/plugins/c2/ 的 services / routes + 判据脚本）。
  门禁强度自知：E1–E5 是【真断言】（项数与集合成员），但判据脚本改动属【判据级】⇒ 不降档。
  契约 C-5 已用哈希锁定采用副本 ⇒ 搬运正确性可判定。
来源: 契约 C-4 / C-5 + 卡 W3-C5a（本卡为 W3-C5a 的**直接执行版**）
base:
  # ---- 源侧（只读素材，E:\ios漏洞 下）----
  - path: E:\ios漏洞\_integration\build\services\chain-router.js
    sha256: cbdd2813e371f5078c1f4ba94a3c5942684acb74901eaedc212acb44ecd98557
    bytes: 9131
    eol: LF
  - path: E:\ios漏洞\_integration\build\services\chain-coruna.js
    sha256: d1370ec9bed8edf2f830e274f27fa7c0413d9cedf94ef16a64703c1379adb340
    bytes: 11360
    eol: LF
  - path: E:\ios漏洞\_integration\build\services\chain-darksword.js
    sha256: 29970bd5a4ef04d1d5e2510b49d9151ba68a91c53319e36691ae1476c2c4fbc0
    bytes: 11402
    eol: LF
  - path: E:\ios漏洞\_integration\build\services\module-packer.js
    sha256: 2c8bf89725e11e51f6d5f134c38e4d49195cc822bc9f7bd753205fa09c576f5c
    bytes: 3533
    eol: LF
  # ---- 产物侧（本卡要改的 3 个）----
  - path: 02-backend-node\src_restored\plugins\c2\services\config-builder.js
    sha256: d8bd4b8ec932ca8f39f1950a6c1aaed1314f6d175f9989792695278ef30576b7
    bytes: 2491
    eol: LF
  - path: 02-backend-node\src_restored\plugins\c2\routes\config.js
    sha256: 09dd494b917ad4c5c0f165d7989578d03fbfae045101e405700820d04f7122f0
    bytes: 2005
    eol: LF
    note: ★ 若已存在则本卡只改其调用行；实测该文件当前存在
allowed_paths:
  - 02-backend-node\src_restored\plugins\c2\services\chain-router.js      # 新建（搬运）
  - 02-backend-node\src_restored\plugins\c2\services\chain-coruna.js      # 新建（搬运）
  - 02-backend-node\src_restored\plugins\c2\services\chain-darksword.js   # 新建（搬运）
  - 02-backend-node\src_restored\plugins\c2\services\module-packer.js     # 新建（搬运）
  - 02-backend-node\src_restored\plugins\c2\services\config-builder.js    # 改（接入 pickChain）
  - 02-backend-node\src_restored\plugins\c2\routes\config.js              # 改（传 device 实参）
  - E:\ios漏洞\_integration\_fix_work\test_chain_router.mjs              # 改 import 指向产物
  - E:\ios漏洞\_integration\_fix_work\verify_i1c1_chain_router_hash.py    # 新建判据
forbidden_paths:
  - "09-docs\\spec\\contracts.md（契约本 C-1…C-5，只读）"
  - "E:\\ios漏洞\\_integration\\gasleak-integrated\\**（契约 C-5 已裁【不采用】）"
  - "05-ios/**（★ 载荷本体，硬约束只读）"
  - "02-backend-node\\templates\\**（属 I1-C2 的 srcDir 产出）"
  - "02-backend-node\\src\\**（扁平版，P-8）"
  - "02-backend-node\\src_restored\\app.js（★ 新增调用点属 I1-C2，不在本卡）"
  - "E:\\ios漏洞\\_integration\\build_unified.ps1（单一写者 = W1-C1）"
  - "01-backend-go/**、03-web-admin/**、04-landing/**、06-android/**"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_i1c1_chain_router_hash.py    # ①动前：须【红】（4 文件不存在），退出码 != 0
  - python _fix_work\verify_i1c1_chain_router_hash.py    # ②动后：须【绿】，退出码 0
  # 4 个新文件各跑一次 node --check
  - node --check 02-backend-node/src_restored/plugins/c2/services/chain-router.js
  - node --check 02-backend-node/src_restored/plugins/c2/services/chain-coruna.js
  - node --check 02-backend-node/src_restored/plugins/c2/services/chain-darksword.js
  - node --check 02-backend-node/src_restored/plugins/c2/services/module-packer.js
  - node --check 02-backend-node/src_restored/plugins/c2/services/config-builder.js
  - node --check 02-backend-node/src_restored/plugins/c2/routes/config.js
  - node _fix_work\test_chain_router.mjs                 # ★ 改 import 指向【产物】后，退出码 0
packages: {}
---

# I1-C1 [R3] 搬运 chain-* 与 module-packer 并接上路由

## 目标

把契约 C-5 已定案的 **4 个文件**搬进产物，并让 `moduleBelongsToChain` 这一层
在**产物内**可用。**本卡不做 `app.js` 的新增调用点**（那是「新造」，属 `I1-C2`）。

## ★ 副本选择（已定，见契约 C-5）—— 本轮已复验

**采用 `E:\ios漏洞\_integration\build\services\` 版**：

| 源文件 | sha256 | bytes |
|---|---|---|
| `chain-router.js` | `cbdd2813e371f5078c1f4ba94a3c5942684acb74901eaedc212acb44ecd98557` | 9131 |
| `chain-coruna.js` | `d1370ec9bed8edf2f830e274f27fa7c0413d9cedf94ef16a64703c1379adb340` | 11360 |
| `chain-darksword.js` | `29970bd5a4ef04d1d5e2510b49d9151ba68a91c53319e36691ae1476c2c4fbc0` | 11402 |
| `module-packer.js` | `2c8bf89725e11e51f6d5f134c38e4d49195cc822bc9f7bd753205fa09c576f5c` | 3533 |

★ **本轮已实测源文件存在且 sha/bytes 与契约 C-5 完全一致**（2026 本轮）。

**不采用** `gasleak-integrated/plugins/c2/services/chain-router.js`
（sha `5714611b…`, 6087 B，硬编码 `['22E240','22E252']` —— **已证伪**）。
**不采用** `_backup_20260926_161237/chain-router.js`（同上 sha，旧件备份）。

## 契约（只读）

受 `09-docs/spec/contracts.md` 约束，**尤其 C-3**：
`entries` coruna **恰 15**、darksword **恰 5**、不含 `ba712ef6…`/`b5135768…`/`tglib`、
**不是 `15 − 2 = 13`**。

## ★ 判据先于实现（判据 9）

**必须先把 `verify_entries_coruna.mjs` 写好并跑到「红」**（该脚本由 `I1-C2` 产出；
若 `I1-C2` 未先行，本卡至少须先跑本卡的 `verify_i1c1_chain_router_hash.py` 到红）。

**本卡修复前天然为红**：4 个文件在产物内**不存在** ⇒ 判据非 0 退出。

★ **E1 与 E2 不相减**：那两个 ID **不在** 15 项内，故**不是 `15−2=13`**。
按「13」验收会**直接放过一个错误实现**。

## 规格（可判定）

1. **逐字节搬运** 4 个文件到 `02-backend-node/src_restored/plugins/c2/services/`：
   `chain-router.js`、`chain-coruna.js`、`chain-darksword.js`、`module-packer.js`
   —— **不得顺手改动**（改后须与源侧 sha256 **逐一比对**证明一致）。

   ★ **落点已确认存在**：`plugins/c2/services/` 当前已有 `config-builder.js`、`device.js`。

2. **`config-builder.js`**：`getConfigJson(channel)` → **`getConfigJson(channel, device)`**，
   接入 `pickChain(device?.userAgent || device?.ua || '')` 与 `unsupported: true` 拒绝分支。

3. **`routes/config.js`**：调用处**传入 device**
   （现为 `getConfigJson(channel || undefined)` —— **缺第二个实参**）。

4. **`test_chain_router.mjs` 的 import 指向产物**
   （`02-backend-node/src_restored/plugins/c2/services/chain-router.js`）
   —— 否则下次仍是**假绿**（**P-3**：该脚本当前测源目录，对产物**零覆盖**）。
   ★ 若不改指向 ⇒ 必须**改名** `test_chain_router_prototype.mjs` **并降低其门禁地位**。

## ★ 本卡与 I1-C2 的边界（重要）

| 项 | 归属 |
|---|---|
| 搬运 4 文件、接 `config-builder`/`routes`、改判据指向 | **本卡** |
| `app.js` 新增调用点、绑 `srcDir`、`templates/` 复制产出 | **I1-C2** |

★ 本卡跑完后，`entries` **可能仍是空的**（因为还没有调用点去同步载荷）
—— **这是预期的**，`entries` 非空是 `I1-C2` 的验收项。

## 不在范围

- **不改 `app.js`**（属 `I1-C2`）
- **不做 C-4 的 `templates/` 复制**（属 `I1-C2`）
- **不改 `build_unified.ps1`**（单一写者 = `W1-C1`）
- 不改 `05-ios/**` 任何文件；不动 `gasleak-integrated/` 副本；不改 `templates/**`
- 不改 `_manifest.sha256`

## 证据要求

- 4 个源文件的 sha256 + bytes **实测值**（与契约 C-5 / 本卡 `base` 比对）
- 4 个产物文件的 sha256 + bytes，**须与源侧逐一相同**
- `config-builder.js` / `routes/config.js` 改前 / 改后 sha256 + diff
- `test_chain_router.mjs` 改前 / 改后 sha256 + **import 指向的实际内容**
- `node --check` 6 个文件的**真实退出码**
- `test_chain_router.mjs` 改指向后的**真实退出码**
- ★ **明确声明**：本卡完成后 `entries` 是否仍为空（预期为空，不构成失败）

## 停靠点

1. 若任一源文件 sha256 / bytes **与契约 C-5 或本卡 `base` 不符** ⇒
   **停下升级**（契约前提失效）
2. 若需改 `build_unified.ps1` 才能持续产出 ⇒ **停下升级**（单一写者 W1-C1 + 脱敏门禁）
3. 若发现 `test_chain_router.mjs` 的断言数与其实际 import 路径**不一致** ⇒
   **登记上报**（**P-1** 形态：把"源目录的成绩"记成"产物的成绩"）
4. 若搬运后 `node --check` 失败（语法/ESM 解析问题）⇒ 停下升级，
   **不得**为了"让它能跑"而修改搬运内容
