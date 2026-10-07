---
id: D0-C1
mode: 实施
wave: P0
depends: []
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R2
定档理由: |
  本卡改的是 06-android/tools/ 下的【载荷解析工具】—— 属 `06-android/**`，
  路径清单定「至少 R2」。
  缺陷性质：AES 模式选错（应为 CTR 却用 CBC）⇒ 解出乱码，且**不报错**（静默出错）
  ⇒ 属"看起来能跑、实际无效"的典型形态。
  ★ 非资金路径、非运行时交付物（是离线分析工具）⇒ 不上 R3。
  门禁强度自知：判据多为结构断言 ⇒ 须补【真跑解密并核对输出】才够。
来源: 完整版本开发方案_终版 §三（"bdecrypt.py 分支错"）
      + 调度本轮实跑确证（mode='AES/CTR/NoPadding'，代码选 CBC）
      + 与 bstage*.py 的三处对照
base:
  - path: 06-android\tools\bdecrypt.py
    sha256: cd127d7f44542891dd17e57ac9286702f2744af04d717327271d73b0aa946fa4
    bytes: 3069
    eol: LF
  - path: 06-android\tools\bstage.py
    sha256: 575df49a22a36e5a8fa5011d77e462103dc77fad2247f6c9b03e5b1a683f662a
    bytes: 2188
    eol: LF
  - path: 06-android\tools\bstage2.py
    sha256: ec1e79e709747c4db3dd520ed7d30d73e4d8769308779db812efd60e7aa31428
    bytes: 3029
    eol: LF
  - path: 06-android\tools\bstage3.py
    sha256: d8493156c990452ce632f4bb10a4ac24790e4823e96037d47561ddc287be7000
    bytes: 2383
    eol: LF
allowed_paths:
  - 06-android\tools\bdecrypt.py
  - E:\ios漏洞\_integration\_fix_work\verify_d0c1_aes_mode.py
forbidden_paths:
  - "09-docs\\spec\\contracts.md（契约本，只读）"
  - "06-android\\tools\\bstage.py / bstage2.py / bstage3.py / unpack.py（★ 本卡只改 bdecrypt.py —— 其余是在用的正确版本，不得动）"
  - "06-android\\stage\\**、06-android\\full\\**（已解包产物，只读）"
  - "E:\\潜客\\**、E:\\ios漏洞\\ios15-17版本漏洞\\**、E:\\IOSusdt\\**（只读素材）"
  - "E:\\ios漏洞\\_integration\\build_unified.ps1（单一写者 W1-C1）"
  - "_manifest.sha256"
verify:
  - python _fix_work\verify_d0c1_aes_mode.py    # ①动前：须【红】，退出码 != 0
  - python _fix_work\verify_d0c1_aes_mode.py    # ②动后：须【绿】，退出码 0
  - python -m py_compile 06-android/tools/bdecrypt.py     # 退出码 0
packages: {}
---

# D0-C1 [R2] `bdecrypt.py` 的 AES 模式选错（应 CTR 却用 CBC）

## 目标

让 `bdecrypt.py` **按 `mode` 字符串里真正的算法段选算法**，并**与 `bstage*.py` 保持一致**。

## ★ 缺陷事实（调度实跑确证）

### 1. 它**已经解出了正确的 mode**，却不用

```python
mode = xhfvif([0x6fb0, 0x6fb4, ...])     # → 'AES/CTR/NoPadding'   ★ 实测
parts = mode.split("/")                   # → ['AES', 'CTR', 'NoPadding']
```

### 2. 但分支**只看段数，不看算法段**

```python
if   len(parts) == 3:                        cipher = AES.new(KEY, AES.MODE_CBC, iv)
elif len(parts) == 2 and parts[1] == "ECB":  cipher = AES.new(KEY, AES.MODE_ECB)
else:                                        cipher = AES.new(KEY, AES.MODE_CBC, iv)
```

**`len(parts) == 3`（= 我们的情况）⇒ 一律 CBC**，**`parts[1]`（`CTR`）从未被用于选算法**。

### 3. ★ 铁证：同目录三个脚本**全部**用 CTR

| 文件 | 行 | 算法 |
|---|---|---|
| `bstage.py` | `:13-14` | `Counter.new(128, initial_value=int.from_bytes(iv,"big"))` + **`MODE_CTR`** |
| `bstage2.py` | `:12` | **`MODE_CTR`** |
| `bstage3.py` | `:12` | **`MODE_CTR`** |
| **`bdecrypt.py`** | `:46` | ❌ **`MODE_CBC`** |

**同一套数据，唯独 `bdecrypt.py` 用 CBC** ⇒ **解出乱码且不报错**（静默出错）。

### 4. 附带的格式差异（★ 执行者须实读确认）

`bdecrypt.py` 的解析格式与 `bstage.py` **不同**：

| | 格式 |
|---|---|
| `bdecrypt.py:12`（docstring） | `[int32 count]` 然后 count × `[int16 nameLen][name][int32 size][data]` |
| `bstage.py:20`（docstring） | 重复 `[int32 size][int16 nameLen][name][data]` |

★ **执行者必须实读两处 docstring 与代码，判断哪个是对的**，**不得凭本卡猜测**。
若确认两者格式不同 ⇒ **以 `bstage.py`（在用版本）为准**，并**在报告中说明**。

## 规格

### (a) 按 `parts[1]` 分派算法

```python
alg = parts[1].upper() if len(parts) >= 2 else "CBC"
if alg == "CTR":
    ctr = Counter.new(128, initial_value=int.from_bytes(iv, "big"), allow_wraparound=True)
    cipher = AES.new(KEY, AES.MODE_CTR, counter=ctr)
elif alg == "ECB":
    cipher = AES.new(KEY, AES.MODE_ECB)
else:                       # CBC
    cipher = AES.new(KEY, AES.MODE_CBC, iv)
```

★ **CTR 必须用 `Counter.new(128, initial_value=iv)`**（与 `bstage.py:13` 一致），
**不得**直接 `AES.new(KEY, AES.MODE_CTR, nonce=iv)`（那会改变计数语义）。

### (b) 删除「else 一律 CBC」兜底

兜底不得无条件选 CBC；须**显式**基于算法段。

### (c) 不得改动 `bstage*.py`

它们是**在用的正确版本**。本卡**只改 `bdecrypt.py`**。

### (d) 若格式也需对齐，须一并修正并说明

按你在 (4) 的实读结论执行。

## ★ 判据先于实现（判据 9）

`verify_d0c1_aes_mode.py`（已写，**先红**）：

| # | 断言 | 红态 |
|---|---|---|
| B1 | 存在按 `parts[1]` 的算法分派（能选中 CTR） | 缺 ⇒ **红** |
| B2 | 含 `AES.MODE_CTR` | 缺 ⇒ **红** |
| B3 | CTR 用 `Counter.new(128, initial_value=iv)` | 缺 ⇒ **红** |
| B4 | 三个 `bstage*.py` 全为 CTR（对照基线） | 绿 |
| B5 | `bstage*.py` 未被改坏（防改过头） | 绿 |
| B6 | 无「else 一律 CBC」兜底 | 有 ⇒ **红** |

★ **B1 曾是我的弱断言**（只匹配 `parts[1]` 是否出现 ⇒ 假绿），
**已修正为"必须能选中 CTR 的分派"** —— 执行者**不得**把它改回去。

## ★ 必须补的真跑证据（门禁越弱审核越深）

结构断言**不足以**证明解密正确。执行者须：

1. 用**真实样本**跑一次解密：`E:\ios漏洞\recon\apk\unpacked\inner_b.apk`
   的 `assets/0gvw74arcr5sml`（★ 若源侧不可用，**如实说明并跳过**，不得编造）；
2. 若跑通 ⇒ 贴出**entry 数量与前几个 entry 的 sha256 前 32 位**；
3. 与 `bstage.py` 的输出**对照**（两者应一致）。

## 不在范围

- 不改 `bstage*.py` / `unpack.py`
- 不改 `06-android/stage/**`（已解包产物）
- 不改 `build_unified.ps1`

## 证据要求

- `verify_d0c1_aes_mode.py` 改前红 / 改后绿两次真实退出码
- `bdecrypt.py` 改前 / 改后 sha256
- `python -m py_compile` 真实退出码
- **真跑解密的输出**（或如实说明为何无法跑）
- ★ 明确声明：`bstage*.py` **未改**

## 停靠点

1. 若 (4) 的格式差异**无法判定**哪个对 ⇒ **停下升级**
2. 若真跑解密发现**输出与 `bstage.py` 不一致** ⇒ **停下升级**（可能不止算法一处错）
3. 若需改 `bstage*.py` 才能对齐 ⇒ **停下升级**
