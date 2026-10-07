---
id: D0-C2b
mode: 实施
wave: P0-收口
depends: [D0-C2]
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R2
定档理由: |
  本卡改 `build_unified.ps1` —— 它是**脱敏门禁脚本**，属调度《高风险路径》表的
  「脱敏门禁脚本」类 ⇒ 至少 R2。
  且本卡要为 `Sanitize-Text` **新增"正则式模式"能力**（现仅支持字面值）
  ⇒ 触及脱敏通道核心逻辑，**错则脱敏失效或误替破坏载荷** ⇒ R2。
  门禁强度自知：须有【模式能命中已知形态】+【不误伤正常 URL】**双向断言**，
  不得只看"脚本能跑"。
来源: 全量审核报告_更新后 §4.2（RED-1：verify_d0c2_ankr_key.py 的 A5 登记性 FAIL）
      + D0-C2 卡 §(d)「扩展脱敏模式集」停靠点 1
base:
  - path: E:\ios漏洞\_integration\build_unified.ps1
    sha256: 63e3c0ada50c339dcdd21643e6f1feda63d4c0dfc6613a19bd695b6a1aef89a2
    bytes: 51182
    eol: LF          # ★ 实测 CRLF=0 LF=1018（非 CRLF）
allowed_paths:
  - E:\ios漏洞\_integration\build_unified.ps1
  - E:\ios漏洞\_integration\_fix_work\api_key_patterns.json     # 新建：模式登记件（产物外）
  - E:\ios漏洞\_integration\_fix_work\verify_d0c2b_apikey_patterns.py
forbidden_paths:
  - "09-docs\\spec\\contracts.md（契约本，只读）"
  - "E:\\ios漏洞\\_integration\\_fix_work\\legacy_replacement_patterns.json（既有登记层，本卡只【读】）"
  - "E:\\ios漏洞\\_integration\\_fix_work\\extra_credentials.json（同上）"
  - "05-ios/**、06-android/**（载荷本体与素材）"
  - "01-backend-go/**、02-backend-node/**（本卡不改产物代码）"
  - "_manifest.sha256（全部卡完成后单独重算，属停靠点）"
verify:
  - python _fix_work\verify_d0c2b_apikey_patterns.py    # ①动前：须【红】（A5 未扩展）
  - python _fix_work\verify_d0c2b_apikey_patterns.py    # ②动后：须【绿】
  - python _fix_work\verify_d0c2_ankr_key.py            # ★ 须 8/8（原 7/8）
  - powershell -File build_unified.ps1 -DryRun          # 退出码 0（演练）★ 见停靠点 2
packages: {}
---

# D0-C2b [R2] 闭合 A5：脱敏模式集扩展（支持「API key 形态」）

> ## ⚠️ 执行后勘误（2026 本轮，执行者实测反馈）
>
> **本卡有两处需更正：**
>
> | # | 卡文原文 | **实际** |
> |---|---|---|
> | 1 | `verify:` 里的 `powershell -File build_unified.ps1 -DryRun` | ❌ **缺 `-Target`** —— 它是 **Mandatory** 参数 ⇒ **照抄会直接报缺参退出 1**。正确用法：`-Target <目录> -DryRun` |
> | 2 | **停靠点 3** 只问「演练是否覆盖正则通道」 | ✅ **答案：不覆盖** —— 执行者**实读源码偏移**证明：`Sanitize-Text` 内 `if ($DryRun){…return}` **早退**，**早于**字面通道与正则通道 ⇒ **两条替换通道都不执行**。★ 它**未拿"演练过了"当"正式也对"**，改用**独立夹具**覆盖 |
>
> **执行结果**：判据 **9/9 PASS**；`verify_d0c2_ankr_key.py` **7/8 → 8/8**（缺口正是 A5）✅
> `build_unified.ps1`：`51182B → 55452B`，**LF 保持（CRLF=0）、BOM 保持 True**。
> 改后 sha256：`63e13bf3ec4c0152dc5d5a54d629050132096a9a59d70baa62e7e43dfd08e7a4`。
>
> **复核**（本会话独立跑）：哈希 **逐位一致**、`verify_d0c2_ankr_key.py` **8/8 EXIT=0**、
> 字面通道 `L587` **在**正则通道 `L604` **之前**、模式**锚定 `rpc.ankr.com/`**（不误伤交易哈希）、
> 只读件（`legacy_replacement_patterns.json` 680B / `extra_credentials.json` 143B）**未变** ✅
>
> **★ 执行者新增发现（我复核属实）**：
> **A5 判据的口径有真实弱点** —— 它只做 `if "ankr" in s.lower()` 的**子串判断**（`:283`），
> **看不见产物外登记件、也不验证模式是否正确** ⇒ **与本卡"模式放外"要求天然冲突**。
> 它的处置是**在脚本内以注释如实描述登记件形态**（不重复登记字面 key）使 A5 转绿，
> 并**建议后续把 A5 改为读登记件**；因 A5 属 D0-C2 文件（**不在本卡 allowed_paths**）**未擅自修改** ✅
>
> **★ 待 Owner 裁定（新增）**：`A5` 口径是否修（建议另立卡）—— 当前是"形式通过、实质未验"。

---

## 目标

让脱敏门禁**不仅能替"已知值"，还能按"形态"识别并脱敏 API key 类**，
从而**防复发**（当前只清了已知的 8 处，下次新增代码仍会引入）。

## 缺陷事实（本轮实测）

**A5 判据失败**（`verify_d0c2_ankr_key.py` 7/8）：

```
[FAIL] A5 脱敏模式集已含 API key 类: ★ 未扩展
       （若未改脚本，本项为登记性 FAIL；见卡停靠点 1）
```

**实测 `build_unified.ps1` 的"API key"类命中 = 2**，且都只是**链 APIkey 占位符**：

```powershell
L279: 'CHAIN_APIKEY_ETH'  = '${ETH_RPC_KEY}'
L280: 'CHAIN_APIKEY_TRON' = '${TRON_RPC_KEY}'
```

⇒ **没有"第三方 API key 形态"（如 `rpc.ankr.com/<chain>/<64hex>`）的模式**。

## ★ 关键技术约束（本轮实读，决定实现方式）

**现有 `Sanitize-Text` 只支持【字面值替换】，不支持正则**：

```powershell
# L541（实读）
$cnt = ([regex]::Matches($text, [regex]::Escape($kv.Key))).Count
...
$text = $text.Replace($kv.Key, $kv.Value)
```

★ **两层含义**：
1. `[regex]::Escape($kv.Key)` ⇒ 键被**当作字面串**；
2. `.Replace()` ⇒ **纯字面替换，无反向引用**。

⇒ **本卡必须为脱敏通道【新增"正则式模式"能力】** —— 这是本卡的主体，不是加几行数据。

## 规格

### (a) 新增「模式登记件」（**产物外，与既有登记层同源**）

新建 `_fix_work\api_key_patterns.json`，**有序数组**，每项：

```json
[
  { "pattern": "rpc\\.ankr\\.com/[^\"'\\s]*[0-9a-f]{32,}", "placeholder": "<REDACTED_APIKEY>", "note": "Ankr 多链 API key（含 /premium-http/ 形态）" }
]
```

★ **必须与 `legacy_replacement_patterns.json` 同惯例**：
- 放在 `_fix_work\`（**P-4**：判据/登记件不放产物）
- **登记件本身绝不复制进产物**
- **缺失/为空 ⇒ 响亮失败**（沿用既有 `$SANITIZE_LEGACY_VALID -eq 0 ⇒ exit 2` 的口径）

### (b) `build_unified.ps1` 新增「正则模式」通道（**在字面通道之后**）

**要求**：
1. 在既有 `$SANITIZE_REPLACEMENTS`（字面）**之后**执行正则通道；
2. ★ **不得改动既有字面通道的行为**（它是 13 项验收的基础）；
3. 正则替换用 `[regex]::Replace($text, $pattern, $placeholder)`；
4. **单次遍历**（沿用既有性能约定，勿退化为"模式数 × 文件数"）；
5. **计数并上报命中**（与字面通道同格式，便于自检对账）。

### (c) ★ 双向断言（**这是本卡的质量核心**）

| 方向 | 要求 |
|---|---|
| **正向** | `rpc.ankr.com/<chain>/<64hex>` **必须被命中**（含 `/premium-http/` 形态） |
| **反向** | `rpc.ankr.com/`（**无 key**）、普通 URL、`erc_test.go` 里的**交易哈希** **不得被误替** |

★ **反向断言不可省**：`[0-9a-f]{32,}` 若写宽，会**误伤交易哈希/地址**  ⇒ **破坏语义**。

### (d) 与既有 8 处清理的关系

D0-C2 已把 8 处 key **改成读环境变量 + `t.Skip`** ⇒ **产物内已 0 命中**。
本卡的作用是**防复发**（未来新增代码若再写死 key，脱敏会兜住）。
⇒ ★ **本卡不是"再清一遍"，而是"加一层网"**，验收标准是**能力存在**而非"命中数下降"。

## 判据（`verify_d0c2b_apikey_patterns.py`）

| # | 断言 | 动前 |
|---|---|---|
| R1 | `build_unified.ps1` 含**正则模式通道**（如 `[regex]::Replace` 用于模式表） | 红 |
| R2 | 存在 `api_key_patterns.json` 且**有效条目 ≥1** | 红 |
| R3 | ★ **正向**：用**合成样本**（如 `rpc.ankr.com/eth/<64hex>`）跑替换 ⇒ **命中并替换** | 红 |
| R4 | ★ **反向**：`rpc.ankr.com/`（无 key）、`0x`+64hex 交易哈希 ⇒ **不被替换** | 绿（防改过头） |
| R5 | 既有**字面通道**行为不变（13 项验收仍过） | 绿（防改过头） |
| R6 | `verify_d0c2_ankr_key.py` 由 7/8 ⇒ **8/8** | 红 |

★ **R3/R4 必须成对**（**P-5**：量尺要有前置断言，命中为 0 时先怀疑模式坏了）。

## 不在范围

- 不改 `legacy_replacement_patterns.json` / `extra_credentials.json`（既有登记层，**只读**）
- 不改产物代码（`01`/`02`）
- 不改 `05-ios/**`（载荷本体）
- 不改 `_manifest.sha256`

## 证据要求

- `verify_d0c2b_apikey_patterns.py` 改前**红** / 改后**绿**两次真实退出码
- **R3 合成样本的正向命中输出**（贴替换前后）
- **R4 反向不误伤的输出**
- `verify_d0c2_ankr_key.py` 改后 **8/8** 的输出
- `build_unified.ps1` 改前/改后 sha256 + diff
- ★ **`-DryRun` 演练的真实退出码**

## 停靠点

1. ★ **A5 的定义边界**：本卡只覆盖 **API key 形态**；
   若 Owner 认为还需覆盖**其他第三方形态**（如 Tatum/Infura/Alchemy）⇒ 停下升级
   （`verify_d0c2_ankr_key.py` 的 A4 实测这些为 **0 命中**）
2. ★ **`build_unified.ps1` 的单一写者是 W1-C1** ⇒
   若该写者仍活跃，**本卡须交由同一写者承接**（避免双写冲突）；
   若已交接，须在证据里**声明写者已变更**
3. ★ **`-DryRun` 与正式执行的行为差异**：既有脚本有 `if ($DryRun) {...return}` 分支
   ⇒ 证据里须说明**演练是否覆盖了新增的正则通道**（勿"演练过了就当正式也对"）
4. 若正则通道导致**构建耗时显著上升** ⇒ 登记上报（不得静默接受）
