# -*- coding: utf-8 -*-
"""T49 · `migration/**` **施工面卫生**判据件（**静态**：不连库、不起服务、不改 `migration/**`）。

★ 断言（三条 + 一条文档）：
  A1 **应用集**必须恰为 `10/20/21/22/31/32/50/51`（8 件）——
     ⛔ 不含 `30-casbin-seed.sql`（本机 MariaDB 报 1064，且已被 `31` 取代）·
     ⛔ 不含 `40-prod-db-hardening.sql`（自述部署期执行·Owner 裁决不在装测环境跑）·
     ⛔ 不含任何 `*-rollback.sql`（会让「期望 schema」undefine；且**字典序先于**对应 forward 件）。
  A2 **迁移件里<ins>不得再有</ins>写死目标库的 `USE`**（★ `T52` 起）——
     对全 `migration/*.sql` 断言**代码级 `USE` == 0**；同时逐件跑 applier 的 `neutralize()`，
     断言**中和后不留他库**（纵深防御仍在）。
     ★ `USE` 判定与哨兵**都复用 applier 的实现**（单源，⛔ 不各写一套 ⇒ 不会漂移）。
     ★ **量尺自检**（"分句器找得到 `USE`"）已**挪进 `--selftest`**，改拿**合成夹具** ⇒ ⛔ 不依赖真实件里还有没有 `USE`。
  A3 **同行中段**也抓得到（`F-T48-A` 的洞）：喂 `SET @x:=1; USE qk_e2e; ALTER …;` ⇒ **必须被改写**；
     ★ **反向**：把判定改回**行首锚定** ⇒ 该用例**必漏**（＝断言必红）。
  A4 `07-db/README.md` 的**醒目警示在位**且**逐字**含「目标库由应用器决定」与「rollback 先于 forward」。

★ 测试杠杆（⛔ 只用于自检，不是产品开关）：
  · 环境变量 `MH_INCLUDE_30=1` ⇒ 把 `30` **放回应用集** ⇒ A1 必须**变红**（V3 变异）。
  · ★ **旧口径（行首锚定）的对照<ins>不走环境变量</ins>** —— 由 `--selftest` 内
    `check_midline(anchor="line")` 直接复现（切 `applier._USE_ANCHOR`）。★ 刻意**不对 applier
    暴露 env 后门**：那等于给 `USE` 中和这道 **P0 护栏**加一个"可关掉"的开关。
    ⇒ 本件**只声明 `MH_INCLUDE_30` 一个 env 杠杆**，并由 **`A5/V6`** 断言「**文档所述 ⇔ 代码真读**」
    （`F-T49-B`：本件文档**先前多声明过一个"行首锚定"的 env 杠杆**，而代码里**无人读它** ⇒ 两处
     对不上；该声明**已删**，并在 `--selftest` 里保留「**注入该声明 ⇒ 必红**」的变异对照）。

用法：
    python verify_migration_hygiene.py            # 对真实树 ⇒ 期望 RESULT=GREEN / EXIT=0
    python verify_migration_hygiene.py --selftest # 跑 V1 负控 / V2 正控 / V3 变异 / V6 杠杆一致性 ⇒ 期望全过
退出码：0 = GREEN；1 = RED；2 = 量尺自检坏。
"""
from __future__ import annotations

import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re
import sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_ad09_schema_migration_diff as A        # ★ 单源：常量与 neutralize 都取自它

REPO = USDT_ROOT
MIG_DIR = os.path.join(REPO, "07-db", "migration")
README = os.path.join(REPO, "07-db", "README.md")

EXPECT_APP = ["10-migration-machine-wallet-bill.sql", "20-hide-scaffold-menus.sql",
              "21-hide-scaffold-menus-actual.sql", "22-hide-prototype-shells.sql",
              "31-casbin-seed-v2.sql", "32-casbin-seed-v3.sql",
              "50-custom-ownership.sql", "51-customusdtnum-agentusdtnum-backfill.sql"]
README_MUST = ["目标库由应用器决定", "rollback 先于 forward"]
V1_CASE = "SET @x:=1; USE qk_e2e; ALTER TABLE t ADD COLUMN c INT;"
V1_VERCOMMENT = "/*!32306 USE qk_e2e */;\nALTER TABLE packet DROP COLUMN custom_user_id;"   # ★ F-T51-A


# ---------------------------------------------------------------- 工具
def _read(p):
    return io.open(p, encoding="utf-8", errors="replace").read()


def _code_uses(text):
    """★ **单源**：直接调 applier 的 `code_level_uses()` —— 词法级（先剥注释/字符串；★ **版本注释
       `/*!…*/` 的内容算代码** ⇒ 其内 `USE` 一样入网；解析不出者记 `<USE 无法解析>`）。
       ⛔ 本件**不另写分句器/判定**（`T53` 口径冻结于 applier）。"""
    return A.code_level_uses(text)


def _app_set():
    """有效 forward 应用集（复用 applier 的排除口径；`MH_INCLUDE_30=1` ⇒ 变异：把 30 放回）。"""
    names = sorted(f for f in os.listdir(MIG_DIR) if f.endswith(".sql"))
    keep = []
    for f in names:
        if f in A.SKIP_EXACT or f.endswith(A.SKIP_SUFFIX):
            if os.environ.get("MH_INCLUDE_30") == "1" and f == "30-casbin-seed.sql":
                keep.append(f)                        # ★ 测试杠杆：放回 30
            continue
        keep.append(f)
    return keep


# ---------------------------------------------------------------- 断言
def check_app_set(fails):
    got = _app_set()
    print("  [A1] 应用集 = %s" % got)
    if os.environ.get("MH_INCLUDE_30") == "1":
        print("       ★ 变异杆已开（MH_INCLUDE_30=1）")
    if got != EXPECT_APP:
        fails.append("A1-应用集≠期望8件：实得 %s" % (got,))
    bad = [f for f in got if f in A.SKIP_EXACT or f.endswith(A.SKIP_SUFFIX)]
    if bad:
        fails.append("A1-应用集含排除项：%s" % bad)
    if "30-casbin-seed.sql" in got:
        fails.append("A1-应用集含 30（已废/本机报 1064）")


def check_use_coverage(fails):
    names = sorted(f for f in os.listdir(MIG_DIR) if f.endswith(".sql"))
    total_use, residue = 0, []
    for f in names:
        raw = _read(os.path.join(MIG_DIR, f))
        total_use += len(_code_uses(raw))
        try:
            after = [d for d in _code_uses(A.neutralize(raw)) if d != A.TMP_DB]
        except AssertionError as ex:
            residue.append("%s → 哨兵抛错：%s" % (f, ex)); continue
        if after:
            residue.append("%s → 残留他库 %s" % (f, after))
    print("  [A2] 全 %d 件 · 代码级 USE 总处数 = %d · 中和后残留他库 = %s"
          % (len(names), total_use, residue if residue else "无 ✓"))
    if residue:
        fails.append("A2-中和后仍有他库 USE：%s" % residue)
    # ★★ T52 **语义翻转**：迁移件里**不得再有**写死目标库的 `USE`。
    #   删前此处是 `total_use < 4 ⇒ 红`（＝「**分句器没失灵**」的**量尺自检**）；
    #   ★ 量尺自检已**挪进 `--selftest`**（改拿合成夹具），此处改判**契约**：
    #      `0` ⇒ 陷阱已拆（绿）；`> 0` ⇒ 又有人写死了目标库（红）。
    if total_use != 0:
        fails.append("A2-迁移件里仍有写死目标库的 USE：%d 处（T52 之后应恒为 0）" % total_use)


def check_midline(fails, anchor=None):
    """A3：同行中段 ＋ ★ **版本注释内**（`F-T51-A`）是否被抓到。anchor='line' ⇒ 用旧口径（应漏）。"""
    saved = A._USE_ANCHOR
    if anchor:
        A._USE_ANCHOR = anchor
    try:
        out = A.neutralize(V1_CASE)
        out_ver = A.neutralize(V1_VERCOMMENT)          # ★ 单源继承：版本注释形态
    finally:
        A._USE_ANCHOR = saved
    caught = ("qk_e2e" not in out)
    caught_ver = ("qk_e2e" not in out_ver)
    print("  [A3] anchor=%s ⇒ 中段抓到 = %s ｜ ★ 版本注释内抓到 = %s"
          % (anchor or A._USE_ANCHOR, caught, caught_ver))
    return caught and caught_ver


def check_readme(fails):
    txt = _read(README)
    miss = [s for s in README_MUST if s not in txt]
    print("  [A4] README 必含 %s ⇒ 缺 %s" % (README_MUST, miss if miss else "无 ✓"))
    if miss:
        fails.append("A4-README 缺逐字短语：%s" % miss)


# ---------------------------------------------------------------- A6（F-T53-A/F-T55-A/F-T56-2A）：DD 面形态矩阵
# ★ T57 扩格：`CREATE|DROP|ALTER` × `DATABASE|SCHEMA` × {纯形态 · 版本注释 · 注释夹令牌 · 换行 · 多语句中段}
_DD_VERBS = ["CREATE", "DROP", "ALTER"]
_DD_OBJS = ["DATABASE", "SCHEMA"]


def _dd_cells():
    """★ 单源形态表（本件与复核 harness 共用）。"""
    cells = []
    for v in _DD_VERBS:
        for o in _DD_OBJS:
            tail = " CHARACTER SET utf8mb3" if v == "ALTER" else ""
            cells.append(("纯   %s %-8s" % (v, o), "%s %s `x`%s;" % (v, o, tail)))
            cells.append(("版注 %s %-8s" % (v, o), "/*!50000 %s %s `x`%s */;" % (v, o, tail)))
            cells.append(("夹令牌 %s %-8s" % (v, o), "%s /*c*/ %s `x`%s;" % (v, o, tail)))
            cells.append(("换行 %s %-8s" % (v, o), "%s\n%s `x`%s;" % (v, o, tail)))
            cells.append(("多语句 %s %-8s" % (v, o),
                          "SET @x:=1;\n/*!50000 %s %s `x`%s */;" % (v, o, tail)))
    cells += [
        ("小写 drop schema",      "drop schema `x`;"),
        ("混合 Create Database", "Create Database `x`;"),
        ("前导注释 ALTER",        "-- lead\nALTER SCHEMA `x` CHARACTER SET utf8mb3;"),
        ("M 版注 DROP SCHEMA",    "/*M!100100 DROP SCHEMA `x` */;"),
        ("反引号对象名",           "DROP SCHEMA `x-y`;"),
        # ★★ T57 修订（`F-T57-1`）：**真多语句**（段末 `;` 直接暴露）—— 旧版「多语句」格用的是
        #    **版注**形态（`;` 被 `*/` 隔开）⇒ **幸免**，正是漏掉该缺陷的原因之一。
        ("真多语句 DROP DB",      "SET @x:=1;\nDROP DATABASE `x`;\nSELECT 1;"),
        ("真多语句 DROP SCHEMA",  "SET @a:=1;\nDROP SCHEMA `x`;\nSELECT 1;"),
        ("真多语句 CREATE SCH",   "CREATE SCHEMA `x`;\nCREATE TABLE t(a int);"),
        ("真多语句 ALTER SCHEMA", "SELECT 1;\nALTER SCHEMA `x` CHARACTER SET utf8mb3;\nSELECT 2;"),
        ("版注＋后续语句",         "/*!50000 CREATE SCHEMA `s` */;\nCREATE TABLE t(a int);"),
    ]
    return cells


DD_POS = _dd_cells()
DD_NEG = [
    ("普通注释里的 DDL", "/* DROP DATABASE x */;"),
    ("字符串里的 DDL",   "INSERT INTO t VALUES ('DROP DATABASE x;');"),
    ("/*! 内非 DDL",     "/*!50000 SELECT 1 */;"),
    ("DROP TABLE",       "DROP TABLE x;"),
    ("ALTER TABLE",      "ALTER TABLE t ADD COLUMN c INT;"),
]


def _dd_healed(out, src):
    """★★ 判据 **五合一**（T57 修订 · `F-T57-3`："判据力须配得上它的名"）：
       ① **保壳**（`/*!`/`*/` 计数不减）② **改写**（≠输入）③ **DDL 净**（**锚整条语句**）
       ④ ★★ **分隔符存活**（`;` 计数不减 —— `F-T57-1`：**吞段末 `;` ⇒ 多语句粘连**）
       ⑤ ★★ **语句数守恒**（代码级语句数一致 —— 同一病的**结构**判据）。
       ★ ④⑤ 是 `T57` 首版漏掉的那两栏：当时只有 ①②③ ⇒ **35/35 全绿的同时「吞;」就在**。"""
    if not ((out.count("*/") >= src.count("*/")) and (out.count("/*!") >= src.count("/*!"))):
        return False
    if out == src:
        return False
    if out.count(";") < src.count(";"):
        return False                                  # ④ 分隔符存活（F-T57-1）
    if len(A._statements(out)[0]) != len(A._statements(src)[0]):
        return False                                  # ⑤ 语句数守恒（结构性粘连）
    spans, mask = A._statements(out)
    return not any(A._DD_ANY_RE.search(A._code_view(out, s, e, mask)[0]) for (s, e) in spans)


def check_dd_face(fails):
    """★ A6（`F-T53-A`）：DD 面形态矩阵 —— 与 `USE` 面同法、同强度。
       ★ 根因是两条支路**不对称**（DD 曾整段替换 ⇒ 吃掉版本注释收尾 `*/` ⇒ 畸形 SQL）。"""
    print("  [A6] DD 面矩阵（保壳 ＋ 中和；⛔ 不整段替换）")
    for name, src in DD_POS:
        out = A.neutralize(src)
        ok = _dd_healed(out, src)
        print("       正 %-16s %s ｜ %s" % ("✓" if ok else "✗", name, out.replace("\n", "\\n")[:46]))
        if not ok:
            fails.append("A6-DD 正例未过：%s ⇒ %r" % (name, out))
    for name, src in DD_NEG:
        out = A.neutralize(src)
        ok = (out == src)
        print("       负 %-16s %s" % ("✓" if ok else "✗", name))
        if not ok:
            fails.append("A6-DD 负控被误改：%s ⇒ %r" % (name, out))


# ---------------------------------------------------------------- A5/V6（F-T49-B）
DOC_LEVER_RE = re.compile(r"\bMH_[A-Z0-9_]+\b")


def _doc_levers(doc_text=None):
    """模块 docstring 里**声明**的 `MH_*` 杠杆。"""
    if doc_text is None:
        txt = _read(os.path.abspath(__file__))
        parts = txt.split('"""')
        doc_text = parts[1] if len(parts) >= 3 else ""
    return set(DOC_LEVER_RE.findall(doc_text))


def _code_levers():
    """代码里**真读**的 `MH_*` env 杠杆（`os.environ["MH_…"]` / `os.environ.get("MH_…"`）。"""
    txt = _read(os.path.abspath(__file__))
    return set(re.findall(r"os\.environ(?:\.get\(\s*|\[\s*)[\"'](MH_[A-Z0-9_]+)[\"']", txt))


def check_levers(fails, doc_text=None):
    """★ A5/V6（`F-T49-B`）：文档声明的 env 杠杆 ⇔ 代码真读的 —— **同名同效**。
       `doc_text` 仅供自检注入（复现旧文档里那句不存在的 `MH_ANCHOR` ⇒ 必须红）。"""
    d, c = _doc_levers(doc_text), _code_levers()
    print("  [A5/V6] 文档声明 = %s ｜ 代码真读 = %s" % (sorted(d) or "[]", sorted(c) or "[]"))
    if d != c:
        fails.append("A5-文档所述杠杆与代码不一致：仅文档有 %s；仅代码有 %s"
                     % (sorted(d - c), sorted(c - d)))


# ---------------------------------------------------------------- 自检
def selftest():
    print("=== 量尺自检（V1/V2/V3）===")
    ok = True

    # V1 负控：同行中段必须被改写
    out = A.neutralize(V1_CASE)
    v1 = ("qk_e2e" not in out) and (A.TMP_DB in out)
    print("  V1 负控（同行中段被改写）= %s ⇒ %s" % (v1, out))
    ok = ok and v1

    # V1 反向：旧口径必漏 ⇒ 证明该断言**能红**
    leaked = not check_midline([], anchor="line")
    print("  V1 反向（旧口径漏过）= %s" % leaked)
    ok = ok and leaked

    # ★ T52：V2 正控**改为合成夹具** —— 真实 4 件的 `USE` 已删 ⇒ ⛔ 不能再拿真语料当量尺。
    synth = "USE qk_e2e;\n\nALTER TABLE t ADD COLUMN c INT;\n"
    neut_s = A.neutralize(synth)
    v2 = (neut_s == synth.replace("USE qk_e2e;", "USE `%s`;" % A.TMP_DB))
    print("  V2 正控（合成件：行首 USE 中和、其余字节不变）= %s" % v2)
    ok = ok and v2
    v2b = (_app_set() == EXPECT_APP)
    print("  V2 正控（应用集 == 期望 8 件）= %s" % v2b)
    ok = ok and v2b
    # ★★ T52：**量尺自检**（原 A2 那条 `total_use >= 4` 的语义挪到这里）——
    #   在**合成语料**上断言「分句器找得到 USE」（⛔ 不依赖真实件里还有没有 USE）
    n_synth = len(_code_uses(synth))
    v2c = (n_synth == 1)
    print("  V2 正控（量尺自检：合成语料上分句器找得到 1 处 USE）= %s（实得 %d）" % (v2c, n_synth))
    ok = ok and v2c
    # ★★ T52：**契约**正控 —— 真实迁移件里代码级 USE **必须为 0**
    n_real = sum(len(_code_uses(_read(os.path.join(MIG_DIR, f))))
                 for f in sorted(os.listdir(MIG_DIR)) if f.endswith(".sql"))
    v2d = (n_real == 0)
    print("  V2 正控（契约：真实 12 件代码级 USE == 0）= %s（实得 %d）" % (v2d, n_real))
    ok = ok and v2d

    # V3 变异：把 30 放回 ⇒ A1 必红
    os.environ["MH_INCLUDE_30"] = "1"
    f2 = []
    check_app_set(f2)
    os.environ.pop("MH_INCLUDE_30", None)
    v3 = any("30" in x for x in f2)
    print("  V3 变异（把 30 放回 ⇒ A1 必红）= %s（失败项 %s）" % (v3, f2))
    ok = ok and v3

    # V6（F-T49-B）：文档所述 env 杠杆 ⇔ 代码真读；★ 变异：注入旧文档那句不存在的杠杆 ⇒ 必红
    f3 = []
    check_levers(f3)
    v6 = (not f3)
    print("  V6 正控（文档/代码一致）= %s" % v6)
    ok = ok and v6
    f4 = []
    check_levers(f4, doc_text="  · `MH_ANCHOR=line` ⇒ 把判定切回旧的行首锚定\n")
    v6b = any("MH_ANCHOR" in x for x in f4)
    print("  V6 变异（注入不存在的 `MH_ANCHOR` ⇒ 必红）= %s（失败项 %s）" % (v6b, f4))
    ok = ok and v6b

    print("SELFTEST=%s" % ("OK" if ok else "BAD"))
    return 0 if ok else 2


def main():
    if "--selftest" in sys.argv:
        return selftest()
    print("=== T49 · migration 施工面卫生判据 ===")
    fails = []
    check_app_set(fails)
    check_use_coverage(fails)
    if not check_midline(fails):
        fails.append("A3-同行中段 USE 未被改写")
    check_readme(fails)
    check_dd_face(fails)
    check_levers(fails)
    print("")
    if fails:
        print("RESULT=RED  %s" % fails)
        return 1
    print("RESULT=GREEN  应用集正确 · USE 全中和 · 中段可抓 · README 警示在位")
    return 0


if __name__ == "__main__":
    sys.exit(main())
