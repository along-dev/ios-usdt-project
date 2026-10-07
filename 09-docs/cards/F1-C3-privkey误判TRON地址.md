---
id: F1-C3
mode: 实施
wave: 1
depends: []
task_branch: 无（本项目非 git，走「内容 sha256 地基」等价规则）
review_level: R2
定档理由: |
  触 10-sweeper/wsweep/privkey.py —— 离线工具，不直接动资金（无链上写），故非真高危；
  但会污染「哪些私钥在手」的账，属【高风险 → 至少 R2】。
  门禁强度自知：本卡 verify 须为【函数级行为断言】（正例/负例成对），不得只看 py_compile。
来源: 09-docs/reports/全量审核报告_独立复核版.md §三 P1-E
base:
  - path: 10-sweeper\wsweep\privkey.py
    sha256: 156d3aba671638af2bf0df547ab2959005938f1e9abaa5bd3e74bf10a8ee7965
    bytes: 10061
    eol: LF
allowed_paths:
  - 10-sweeper\wsweep\privkey.py
  - E:\ios漏洞\_integration\_fix_work\verify_f1c3_privkey_tron41.py
forbidden_paths:
  - "09-docs\\spec\\contracts.md（契约本，只读）"
  - "10-sweeper\\wsweep\\sweep.py（★ 互斥接入已裁【不做】，见 V0 D-2，不在本卡）"
  - "01-backend-go/**、02-backend-node/**、05-ios/**、06-android/**"
  - "_manifest.sha256"
verify:
  - python -m py_compile 10-sweeper/wsweep/privkey.py    # 退出码 0
  - python _fix_work\verify_f1c3_privkey_tron41.py       # ①动前：须【红】，退出码 != 0，留证
  - python _fix_work\verify_f1c3_privkey_tron41.py       # ②动后：须【绿】，退出码 0
packages: {}
---

# F1-C3 [R2] `privkey.py` 把 TRON 地址误判为私钥

## 目标

让 `41` + 40hex（总长 **42 位** hex）**被识别为 TRON 地址并拒绝**，而不是被规范化成私钥。

## 缺陷事实（本轮实读）

`10-sweeper/wsweep/privkey.py:128-132`：

```python
# 21 字节 TRON 形态：41 + 40hex  =>  总长 42 位 hex
if len(h_clean) == 42 and h_clean.startswith("41"):
    v = int(h_clean[2:], 16)
    if is_valid_privkey_int(v):
        return f"{v:064x}", "hex_tron41", "TRON 0x41 前缀写法"
```

**问题**：`41`+40hex 是 **TRON 地址**的 21 字节形态（`41` 是地址版本字节）。
把它 `int(h_clean[2:], 16)` 后左侧补零成 64 位 ⇒ **派生出一个幻影地址**。

**对比**：同文件 `:156-157` 已正确拒绝**纯 40 位 hex**（`"40 位 hex 是 EVM 地址，非私钥"`）
⇒ 作者已有「地址 ≠ 私钥」意识，**只是漏了 `41` 前缀这条路径**。

**后果**：TRC20-USDT 合约地址等 `41`+40hex 串会被当成私钥，
污染"哪些私钥在手"的判断，并可能触发对幻影地址的后续操作。

## 规格

### (a) `41`+40hex → 拒绝

**两处**（`:129` 的 42 位、`:136` 的 66 位）**都**改为返回 `(None, None, <说明>)`，
说明文案须指明「**TRON 地址形态，非私钥**」。

### (b) ★ 真正的 TRON 私钥形态必须仍能识别（防改过头）

★ 这是本卡**最关键**的一点：**不能把 TRON 私钥一起拒了**。
TRON 私钥是 **64 位 hex**（与 EVM 同长），由 `:142-146` 的标准 64 位分支处理，
**与 42 位分支无交集** ⇒ 拒绝 42/66 位分支**不应**影响 64 位私钥。

执行者**必须**用一个**真实的 64 位 TRON 私钥**做正例回归，证明没被误伤。

### (c) 不得改动其他形态的判定

`hex_0x` / `hex_bare` / `hex_padded` / `wif_*` / 助记词等分支**一律不动**。

## ★ 判据先于实现（判据 9）

`verify_f1c3_privkey_tron41.py` 用例矩阵（**必须成对**）：

| # | 输入 | 期望 | 红态（改前） |
|---|---|---|---|
| R1 | `41` + 40hex（**42 位**） | 拒绝（`None`） | **返回私钥** ⇒ 红 |
| R2 | `0x41` + 40hex 的 **66 位**形态 | 拒绝（`None`） | **返回私钥** ⇒ 红 |
| R3 | **64 位** hex 私钥 | 接受，`form` 正确 | 绿（防改过头） |
| R4 | `0x` + 64 位 hex | 接受 | 绿（防改过头） |
| R5 | 纯 40 位 hex | 拒绝 | 绿（既有行为，不得回退） |
| R6 | **`41` 开头的 64 位真实私钥** | 接受 | 绿（★ 边界用例） |

★ **R6 是本卡的边界用例**：`41` 开头的 **64 位**是**合法私钥**，
与 `41` 开头的 **42 位**（地址）**长度不同** ⇒
判据必须靠**长度**区分，**不得靠前缀**。执行者须显式构造此用例证明实现用的是长度判断。

## 不在范围

- **不改 `sweep.py`** —— 互斥接入**已裁为不做**（见 `V0` 裁决 **D-2**），本卡不涉及
- 不改其他 9 链相关模块

## 证据要求

- `verify_f1c3_privkey_tron41.py` 改前红 / 改后绿两次真实退出码
- R1–R6 **六条用例各自的真实输出**（含被拒绝时的 reason 文案）
- `privkey.py` 改前 / 改后 sha256
- `python -m py_compile` 退出码

## 停靠点

1. 若发现 `41`+40hex 之外还有**其他地址形态**被误当私钥 ⇒ **登记上报**，不扩大范围
2. 若 R6（`41` 开头 64 位私钥）无法构造 ⇒ 停下升级（判据不完整）
3. ★ 若执行者认为应**同时**在 `sweep.py` 加互斥 ⇒ 停下升级（**D-2 已裁不做**）
