---
id: W1-C13
mode: 实施
wave: 1
depends: []
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R2
定档理由: |
  命中「**产出或修改判据本身**」—— 本卡要改 `acceptance_final.ps1`（属**判据级清单**）⇒ **至少 R2**。
  门禁强度自知：本卡 verify 含**行为断言**（对**重建产物**实跑门禁、断言 `EXIT=0` 且 `A1=0`），
  不因"门禁绿了"降档 —— 它的绿必须靠**真的重建一次**才拿到。
来源: |
  **Owner 裁「载体集未收口 ⇒ (甲) 另立小卡做载体集统一」**（⌛2026-09-28 经中转方转达）。
  本卡即台账 `L065 §3` 待裁 ① 的 **(甲)** 路；依据 ＝ 审核者 A 的 `F-2`＋B 的实测（`L068`）＋本线 `L067`。
  ⛔ 未被选中的（「明文接受该残留」·「等双审回来再裁」）**不得以任何形式下发**，只进登记。
base:
  - path: E:\ios漏洞\_integration\_fix_work\acceptance_final.ps1
    sha256: b8c8b601b37f6073808319da69375d9784a2922d437353ebb62b466e415d8fdb
    bytes: 12612
    eol: LF
base_说明: |
  ★ 本卡的 baseline 是**该件现读**（`W1-C10` 已落地后）—— 本卡**只改这一个文件**（卡内 `allowed_paths` 仅此一件）。
  ★ **残留脆弱点（如实登记）**：base 取**真路径**（非 `_dispatch` 副本）⇒ 真件此后被任何卡改动都会使本行 DIFF（那是**预期**）。
allowed_paths:
  - E:\ios漏洞\_integration\_fix_work\acceptance_final.ps1
forbidden_paths:
  - "09-docs\\spec\\contracts.md（契约本 C-1…C-5，生产卡只读）"
  - "E:\\USDT项目\\**（★ **产物由重建生成**；本卡**不得手改产物**）"
  - "E:\\ios漏洞\\_integration\\build_unified.ps1（单一写者 = W1-C1/W1-C9/W1-C10，本卡只读）"
  - "E:\\ios漏洞\\_integration\\_fix_work\\verify_redaction_reverse.py · verify_w1c1_credentials.py · extra_credentials.json（本卡只读）"
  - "E:\\潜客\\**、E:\\ios漏洞\\ios15-17版本漏洞\\**、E:\\IOSusdt\\**（只读）"
  - "05-ios/**、06-android/**、03-web-admin/**、04-landing/**"
  - "_manifest.sha256"
verify:
  # ★★ 本卡的真鉴别力：**对<ins>重建产物</ins>**跑门禁 ⇒ 从 `EXIT=2/A1=3` 变 `EXIT=0/A1=0`
  #    （coruna 三行**落进 `A2` 载体桶**，不再算缺陷）
  #    ① 先在【空的临时目标目录】上实跑构建（脚本可参数化 `-Target`，**不碰主树**）：
  #       `build_unified.ps1 -Target <T>`；★ 它只写 `-Target`（已核：不碰 `_build_ws`）⇒ 对临时目录安全
  - powershell -ExecutionPolicy Bypass -File E:\ios漏洞\_integration\build_unified.ps1 -Target "<临时目录T>"
  #    ② 对【同一个 T】跑门禁 —— 这是本卡的核心断言
  - powershell -ExecutionPolicy Bypass -File E:\ios漏洞\_integration\_fix_work\acceptance_final.ps1 -Target "<临时目录T>"
  #       ★ 期望 **`EXIT=0`** 且 **`A1) 缺陷命中: 0`**；`A2) 已知载体命中` 应包含 coruna 那 3 行（≈16 条量级）
  #    ③ 回归：对**主树**与 **`W1-C1` 副本**仍须 `EXIT=0`
  - powershell -ExecutionPolicy Bypass -File E:\ios漏洞\_integration\_fix_work\acceptance_final.ps1 -Target "E:\USDT项目"
  - powershell -ExecutionPolicy Bypass -File E:\ios漏洞\_integration\_fix_work\acceptance_final.ps1 -Target "E:\_dispatch\W1-C1\USDT项目"
  #    ④ ★ 输入锚：上列每条**跑前与跑后**各读一次 `acceptance_final.ps1` 的 sha256，**必须同值**（证明读数未被并发写污染）
  #    ⑤ PS 保真（P-6）：BOM 前三字节 `efbbbf` ＋ `Parser::ParseFile()` 0 错
packages: {}
---

# `W1-C13` [R2] 载体集统一（**acceptance 侧对齐 build 侧**）—— 只加**一条** type

## 目标（一句话）

把 `acceptance_final.ps1` 的 `$CARRIER_TYPES` **补上 `CORUNA_COLLECT_GUARD_PASS`**（**6 → 7**），
与 `build_unified.ps1` 的 `$SANITIZE_CARRIER_TYPES`（**7 条**）对齐 ⇒
**对重建产物跑 `acceptance_final.ps1` 从 `EXIT=2 / A1=3` 变 `EXIT=0 / A1=0`**（coruna 那 3 行落进 **`A2` 载体桶**）。

## ★★ 它与 `W1-C9`（A2）的关系 —— **同一事实的两侧对齐，不是新判定**

- **`W1-C9` 把该 type 加进了<ins>build 侧</ins>**载体集（`$SANITIZE_CARRIER_TYPES`）；
- **本卡把<ins>同一判定</ins>补到 acceptance 侧**（`$CARRIER_TYPES`）。
⇒ **两侧说的是同一件事**（"该值必然残留在二进制载荷/演示夹具内 ⇒ 按值降级为设计取舍"），
**本卡不引入任何新规则、不改变判定语义**，只是把两侧口径对齐。**请勿把它读成"新判定"**。

## ★ 本线现读的事实（供你核对，不要凭记忆）

| 侧 | 变量 | 条目数 | 独有 |
|---|---|---|---|
| `build_unified.ps1` | `$SANITIZE_CARRIER_TYPES` | **7** | `CORUNA_COLLECT_GUARD_PASS` |
| `acceptance_final.ps1` | `$CARRIER_TYPES` | **6** | —— |

（交集 6 条、差集恰 1 条；本线已用平衡括号解析复算，非按行窗口。）

## ★★ 一条**必须一并登记、但<ins>不在本卡范围</ins>**的事实（本线 `L067` 查出、审核者 A `L068` 复合、同侪 `⌛2026-09-28` 独立核全）

**该"载体 type"族是<ins>四处</ins>，不是两处** —— `verify_redaction_reverse.py:54-56` 的注释**逐字**写着：
> 「与 `build_unified.ps1` / `acceptance_final.ps1` / **`sanitize_target.ps1`** 保持一致。」

**四处现读（同侪独立核，本线复核一致）**：

| 实现 | 条数 | 含 `CORUNA_COLLECT_GUARD_PASS`？ | 本卡是否动它 |
|---|---|---|---|
| `build_unified.ps1` | **7** | ✅ 有 | **否**（它是对齐的**目标侧**） |
| `acceptance_final.ps1` | **6** | ❌ 无 | ★ **本卡改它**（6 → 7） |
| `verify_redaction_reverse.py`（D4，`:57-60`） | **6** | ❌ 无 | ⛔ **不在 `allowed_paths` ⇒ 只登记、不得改** |
| `sanitize_target.ps1`（`:39`） | **6** | ❌ 无 | ⛔ **不在 `allowed_paths` ⇒ 只登记、不得改** |

⇒ **本卡按 Owner 裁决只对齐 `acceptance_final.ps1` 一侧**（那是"两处门禁口径一致"的直接落点、也是**观测到的那条红**的直接成因）；
**但四处并未全齐**：本卡落地后将是 **`build`/`acceptance` 7 vs `D4`/`sanitize_target` 6**。
★★ **这份点名单<ins>只是登记</ins>** —— ⛔ **不是授权**：**不得**据它去改 D4 或 `sanitize_target.ps1`（那两处属**另一条线**，改即**范围扩张**）。
★ **请调度在关单时把这条作为已知残余上报 Owner**：**四处里两处已齐、另两处仍差 1 条**（是否再统一 = **另一个决定**，须**另行裁决**）。
★ 之所以把四处**全列出来**：避免"**只改了被点名的那一处**"那种**半修**（本项目 `E-102` 家族：以局部代替整体）。

## 规格（可判定）

1. 在 `acceptance_final.ps1` 的 `$CARRIER_TYPES` 里**追加** `'CORUNA_COLLECT_GUARD_PASS'`（**6 → 7**）。
   ★ **保持数组语法**：PowerShell `@()` 数组字面量**不允许尾随逗号**（末元素补逗号、新末元素**不带**逗号）。
2. **不得**改任何其它模式、**不得**改判定逻辑、**不得**改 `$CARRIER_TYPES` 之外的任何内容。
3. **不改产物**（产物由重建生成）；**不改** `build_unified.ps1`；**不改** `_manifest.sha256`；**不改契约本**。

## 不在范围

- 不改 `verify_redaction_reverse.py` 的 `CARRIER_TYPES`（属上面那条**登记项**）
- 不改 `sanitize_target.ps1` 的 `$CARRIER_TYPES`（同上；且该件另有卡）
- 不改 `build_unified.ps1`（它本就是 7 条，是对齐的**目标侧**）

## 证据要求

- ★ **重建产物上** `acceptance_final.ps1` 的**改前 / 改后**两次真实读数：`EXIT` 与 `A1`／`A2`（改前应 `EXIT=2/A1=3`；改后应 `EXIT=0/A1=0` 且 coruna 3 行在 `A2`）
- 对**主树**与 **`W1-C1` 副本**的两条回归的真实退出码
- `acceptance_final.ps1` 改前 / 改后 sha256 ＋ bytes；**`$CARRIER_TYPES` 条目数（6 → 7）**的命令与输出
- ★ **输入锚**：每条门禁**跑前/跑后**的该脚本 sha256（须同值）
- ★ 声明：**产物 `E:\USDT项目` 一个字节未动**（贴出 `verify_card_baselines.py` 读数或等价证据）
- PS 保真：BOM 前三字节（hex）＋ `Parser::ParseFile()` 输出

## 停靠点

1. 若**主树**上的读数（本卡改前）**不是** `EXIT=0`（它现读是 `EXIT=0/A1=0`）⇒ **停下报我**（产物已被改过，前提需重核）。
2. 若发现 **`$CARRIER_TYPES` 之外的载体集也在本件内**（例如 `acceptance_final.ps1` 里还有第二张 type 表）⇒ **只登记、不改**，报我。
3. 若你判断**该 type 加入载体集会掩盖真实缺陷**（即 coruna 那 3 行**确实应当**算缺陷）⇒ **停下升级**（那是 Owner 的取舍）。
4. 若四处载体集的**差异不止这一条**（例如 D4 的 `CARRIER_TYPES` 还有别的独有项）⇒ **只登记**，报我。
