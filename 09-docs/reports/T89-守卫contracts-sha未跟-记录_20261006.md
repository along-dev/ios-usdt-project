# T89 记录 —— 两处守卫钉的 `contracts.md` `sha` **没跟着改**（`V8` FAIL 的根因）

> **卡**：`09-docs/cards/T89-守卫contracts-sha未跟.md` @ `088a8c622dc8187836e22680618d624bde8867a136268cda012aef8b36c577f1` / 3544（★ 现算已核 ✓）
> **档**：**R1**（判据／守卫面）｜ **来源**：`T85` 的独立发现（本线勘出）｜ **执行**：本会话 ｜ **收口/提交**：总调度第六任
> **⌛2026-10-06** ｜ ⛔ **未做 git 写** · ⛔ **未改 `contracts.md` 内容**（★ 卡明令：只改守卫钉的值）· ⛔ 未碰 `05-ios/**`／`iso_run.py`／`chain-router.js`／`_manifest.sha256`

---

## 〇 · 结论

★ **两处守卫钉的值已与 `contracts.md` 现态一致** ✓ ｜ ★ **判据 `V8` 由 `FAIL` 转 `PASS`**（`6/8 → 7/8`）✓ ｜ ★ **并落了防再犯机制**（两处紧邻注释 ＋ 一条命令重算）✓

**受改件（两件）**

| 件 | 改前 sha256 | 改后 sha256 | 字节 |
|---|---|---|---|
| `E:\USDT项目\rollback.ps1` | `1c5538d5bf40d36adf94fad5001b4040d8a19634e8fd5d2d52af555fde6e3cc2` / 5182 | **`0a6e9a2f10ad4304faa157a60bd0f05ee79c32bc8be2d334cc3b40aa3035cb9f`** / **5994** | +812 |
| `E:\ios漏洞\_integration\_fix_work\verify_d4c2_credentials.py` | `443877a3770dee53e3181ae32d136d071cac0db0dc53ee9172c9a57e2124150c` / 13410 | **`e39071ed60d2c6ec8becbd5e9edde0a013c3a6e7adee07120cc1f1304bc9f379`** / **14111** | +701 |

---

## 一 · `V1` 先证「漂」（★ 留两边原文）

```
contracts.md 现算 sha256 = 0e03048ddfbe6945dba0cfda5c9dae17b3b50b9ac485a83f921913e49e337358  (10662 B)

rollback.ps1:34
    @{ Path = '09-docs\spec\contracts.md'; Expect = 'f80a2ead6736d5f5aff70e72e3aa7de1c7cc63f93a604fb6eeb4a163059f925c' }
verify_d4c2_credentials.py:73
    r"09-docs\spec\contracts.md": "F80A2EAD6736D5F5AFF70E72E3AA7DE1C7CC63F93A604FB6EEB4A163059F925C",
```
⇒ ★★ **两边均 `f80a2ead…` ≠ 现算 `0e03048d…`** ⇒ **漂移成立** ✓

★ **停止条件检查**（卡的："若两处守卫语义不是'钉内容 sha' ⇒ 停"）：★ `rollback.ps1` 的 `$GUARDS` 是 `{Path, Expect}` 的**内容 sha 表**、`verify_d4c2_credentials.py` 的 `AUTH_BASELINE` 是 `{路径: 内容 sha}` ⇒ ★ **两处语义都是"钉内容 sha"** ⇒ **不触发停止条件** ✓

---

## 二 · `V2` 修后 —— 两处值 ＝ 现算 `sha`

```
实际 sha       = 0e03048ddfbe6945dba0cfda5c9dae17b3b50b9ac485a83f921913e49e337358
rollback.ps1   = 0e03048ddfbe6945dba0cfda5c9dae17b3b50b9ac485a83f921913e49e337358  => 匹配 ✓
d4c2 判据      = 0E03048DDFBE6945DBA0CFDA5C9DAE17B3B50B9AC485A83F921913E49E337358  => 匹配 ✓
```

★★ **口径（★ 两处不同，⛔ 不可照抄）**：★ `rollback.ps1` 的 `Expect` 写**小写**（比对时 `(Get-FileHash …).Hash.ToLower()`）｜ ★ `verify_d4c2_credentials.py` 写**大写**（比对时 `.hexdigest().upper()`）—— ★ 已**分别按各自口径**写入 ✓

★ **`git diff --numstat -- rollback.ps1`＝`8 1`**：★ 删的那 `1` 行 ＝ **被换掉的旧 `Expect` 行**（★ 非条款、非其它内容）✓

---

## 三 · `V3` 判据复跑（★ 真退出码）

```
$ python verify_d4c2_credentials.py            （cwd = 树外 _fix_work；PYTHONUTF8=1）
  [PASS] V1  递归 92 文件不含 <REDACTED_PASSWORD>; 残留: 无
  [PASS] V2  递归 92 文件不含原 JWT x3; 残留: 无
  [PASS] V3  apidoc.txt 不含原 AccessKey#1/#2 与 SecretKey; 残留: 无
  [FAIL] V4  11-payment\pw_privesc.py 逆推不等; 11-payment\pw_privesc2.py 逆推不等
  [PASS] V5  py_compile 36 个 .py: 全部通过
  [PASS] V6  json.loads 15 个 .json: 全部通过
  [PASS] V7  eol 核对 28 目标文件一致; __pycache__ 已删且 V5 后未重建; 异动: 无
  [PASS] V8  守护: _manifest.sha256 + contracts.md 未改          ← ★★ FAIL → PASS
结果: 7/8 PASS          EXIT=1
```

⇒ ★★ **`V8` 已由 `FAIL` 转 `PASS`**（★ 修前同一命令为 `6/8`、`V8 FAIL`；★ 本卡只动守卫值 ⇒ **只此一项翻转**）✓
★ 余下唯一 `FAIL` 是 **`V4`**（`pw_privesc.py`／`pw_privesc2.py` 逆推不等）—— ★ **既有**、★ 已由总调度裁定**单独登记**、⛔ 不并入本卡 ✓

---

## 四 · `V4` 防再犯机制（★ 卡的硬要求）—— 两条都落

★ 卡给二选一，★ **本卡<两条都做**>（且**不新增文件** —— 本仓 `.gitignore:111` 的模式是 `*_work/`，★ 我这类证据目录正落在该模式内、**不进 git**，故机制**落在两件自身的注释里**，★ 才能随件分发）：

1. ★★ **紧邻注释**（★ 就写在那张常量表的正上方，改的人一定看见）：
   - `rollback.ps1:31-39`（`$GUARDS` 上方）
   - `verify_d4c2_credentials.py:72-79`（`AUTH_BASELINE` 上方）
   ★ 两处注释**互相点名对方**（"本表与 `<另一个文件>` 的 `<那张表>` 钉的是同一批件 ⇒ 两处必须同步改"），★ 并写明**只改一处会怎样**（`-Guard` 报 `VIOLATED` ／ 判据 `V8` FAIL）。
2. ★★ **一条命令重算**（★ 直接写在注释里，可复制即用；★ 在仓库根跑）：
   ```
   python -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" 09-docs/spec/contracts.md
   ```
   ★ 并注明**两处大小写口径不同**（★ 这正是上一轮漏跟的一个陷阱面）。

★★ **机制的量尺**（`_T89_work_20261006/t89_check.py`，★ 只读、⛔ 不改件）：
```
正控 第 1 次 ⇒ T89_OK   EXIT=0
正控 第 2 次 ⇒ T89_OK   EXIT=0          ← ★ 复跑一致
负控（喂伪造 sha）⇒ T89_BAD  EXIT=1      ← ★ 尺能红
```
★ **正控 ×2 ＋ 负控** 成对 ⇒ ★ **判据既"能过"也"能红"** ✓

---

## 五 · 边界自证（★ 卡 §三 明令）

- ★★ **⛔ 未跑 `rollback.ps1 -Guard`** —— ★ 因它第 `29` 行会 `git config --global --add safe.directory …` ⇒ **属全局写** ⇒ ★ **本卡用<静态核>替代**：★ 直接**读两处常量**与**现算 `sha`** 比对（§二 就是那次静态核）✓；★ 总调度亦**不跑**该脚本（★ 双方一致）✓
- ★ **`contracts.md` 内容未动**：★ 本卡**未改它一个字节**（★ 只改了两处守卫钉的值）✓
- ★ **编码面复核**（★ 承 `W1-C1` 的 BOM 截断事故）：★ `rollback.ps1` **BOM 仍在**（`efbbbf`）· ★ 两件**行尾均保持原样**（**LF**，无 CRLF）· ★ 字节数**只增不减**（5182→5994／13410→14111）⇒ ⛔ **无截断** ✓
- ★ **语法面**：★ `python -m py_compile` **通过** ✓ ｜ ★ `rollback.ps1` 的 **PowerShell `PSParser::Tokenize` 解析 ⇒ `PARSE_OK`（零错误）** ✓
- ★ ⛔ **未做 git 写** ✓ ｜ ★ 附件件：`rollback.ps1`（仓内）· `verify_d4c2_credentials.py`（树外）✓

---

## 六 · 附带（★ 承 `T85`，供后人）

- ★★ **`contracts.md` 被 `162` 个仓内件引用** ⇒ ★ **若将来真要改它的内容，登记面须覆盖这 `162` 处**（★ 且**必须同步本卡这两处守卫**）✓
- ★ 本卡修的是 **⌛2026-10-04 那次更正（给 `contracts.md` 抬头加更正行）的<副作用**>** —— ★ **那次改了件、忘了守卫**；★ 这正是 `E-469`（"改 `sha` 先全仓扫引用面再登记"）的**同族实例** ✓

---

## 七 · 环境读数与证据路径

- ★ 证据留存（树外，⛔ 不污染仓库）：`_T89_work_20261006\{t89_check.py, pos1.out, pos2.out, neg.out}`
- ★ 判据本体：`E:\ios漏洞\_integration\_fix_work\verify_d4c2_credentials.py`（改后 `e39071ed…`）
- ★ ⛔ 未连库 · ⛔ 未启停服务 · ⛔ 未起 `8900` ✓

---

## 八 · 水位

★ 现读：`304,005 / 1,000,000 ＝ 30%`（`get_usage self`）⇒ ★ 远低于 75%／90% 门槛 ✓

---

*本件由本会话产出 · ⌛2026-10-06 · 两处守卫已同步 ＋ 防再犯机制就位 · ⛔ 未做 git 写 · ⛔ 未改 `contracts.md`*

> ★ **T100 掩码更正（⌛2026-10-06）**：本件正文原含**明文口令**（`«PW»`，长度 8、`sha256` 前 8 ＝ `7ee7016b`），已由 `T100`（`A＋` 案）**掩码为 `<REDACTED_PASSWORD>`**；★ 原文留痕见 `09-docs/reports/T100-PW明文17件定性_20261006.md` §一（⛔ 值不复抄）。
