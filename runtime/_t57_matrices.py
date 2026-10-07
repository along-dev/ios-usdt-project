# -*- coding: utf-8 -*-
"""T57 修订 · 双面矩阵（DD 面扩格 ＋ USE 面 14 格）
   ★ DD 判据 **五合一**：保壳 ＋ 改写 ＋ DDL净(锚整条语句) ＋ ★**分隔符存活** ＋ ★**语句数守恒**
   ★★ 另加 **引擎「产出可执行」对照**（`F-T57-3`）：把**输入**与**产出**分别喂给隔离 MariaDB，
      只在「**原件不报错、产出报错**」时判「产出畸形」（同名量对照 ⇒ ⛔ 不把量尺自身的产物算成缺陷）。
      ★ 引擎段只碰**我自己的 scratch 库** `qk_t57_scr`（跑前重建／跑后 DROP）；单元格里的库名会被换成它。
   用法：python _t57_matrices.py [<装置路径>] [<标签>] [--engine]"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import importlib.util, os, re, subprocess, sys

FW = IOS_ROOT + r"\_integration\_fix_work"
MY = os.path.join(FW, r"_toolchain\mariadb-11.4.4-winx64\bin\mysql.exe")
SCRATCH = "qk_t57_scr"
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
ENGINE = "--engine" in sys.argv
TARGET = ARGS[0] if ARGS else os.path.join(FW, "verify_ad09_schema_migration_diff.py")
LABEL = ARGS[1] if len(ARGS) > 1 else "现版"

DD_ANY = re.compile(r"(?is)(?<![A-Za-z0-9_])(create|drop|alter)\s+(database|schema)\b")
USE_POS = [("①块注释夹令牌", "USE qk_e2e /* prod */;"), ("②行注释夹令牌", "USE qk_e2e -- prod\n;"),
           ("③换行＋块注释", "USE qk_e2e\n/* prod */;"), ("④同行中段", "SET @x:=1; USE qk_e2e; ALTER TABLE t ADD COLUMN c INT;"),
           ("⑤前导行·块注释", "-- lead\n/* lead */\nUSE qk_e2e;"), ("⑥反引号库名", "USE `qk_e2e`;"),
           ("⑦大写", "USE QK_E2E;"), ("⑧版本注释", "/*!32306 USE qk_e2e */;")]
USE_NEG = [("N1字符串内", "INSERT INTO t VALUES ('USE qk_e2e;');"), ("N2列名 use", "SELECT `use` FROM t;"),
           ("N3 USE_前缀", "USE_DB_X = 1;"), ("N4 UPDATE", "UPDATE t SET a = 1;"),
           ("N5 user", "SELECT user FROM t;"), ("N6注释内", "/* USE qk_e2e */;")]


def load(p, n):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


A = load(TARGET, "A")
H = load(os.path.join(FW, "verify_migration_hygiene.py"), "H")   # 形态表**单源**


def healed(out, src):
    """★ 五合一（与 hygiene._dd_healed 同口径）。"""
    if not ((out.count("*/") >= src.count("*/")) and (out.count("/*!") >= src.count("/*!"))):
        return False, "保壳✗"
    if out == src:
        return False, "未改写✗"
    if out.count(";") < src.count(";"):
        return False, "分隔符✗"
    if len(A._statements(out)[0]) != len(A._statements(src)[0]):
        return False, "语句数✗"
    spans, mask = A._statements(out)
    if any(DD_ANY.search(A._code_view(out, s, e, mask)[0]) for (s, e) in spans):
        return False, "DDL残留✗"
    return True, "五合一✓"


def sql(s, db=None):
    cmd = [MY, "--skip-ssl", "-h", "127.0.0.1", "-P", "13306", "-u", "root", "-B", "-N"]
    if db:
        cmd.append(db)
    p = subprocess.run(cmd + ["-e", s], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def to_scratch(t):
    return re.sub(r"`[A-Za-z_-]+`", "`%s`" % SCRATCH, t)


def engine_check(src, out):
    """★ 同名量对照：只在「原件不报错、产出报错」时判产出畸形。"""
    sql("DROP DATABASE IF EXISTS `%s`;" % SCRATCH)
    sql("CREATE DATABASE `%s` DEFAULT CHARACTER SET utf8mb4;" % SCRATCH)
    rc_r, _o, err_r = sql(to_scratch(src), db=SCRATCH)
    sql("DROP DATABASE IF EXISTS `%s`;" % SCRATCH)
    sql("CREATE DATABASE `%s` DEFAULT CHARACTER SET utf8mb4;" % SCRATCH)
    rc_o, _o2, err_o = sql(to_scratch(out), db=SCRATCH)
    sql("DROP DATABASE IF EXISTS `%s`;" % SCRATCH)
    return (rc_o != 0 and rc_r == 0), err_o


reds = []
print("=== DD 面矩阵（%d 正例 ＋ %d 负控）· %s ｜ 引擎对照=%s ===" % (len(H.DD_POS), len(H.DD_NEG), LABEL, ENGINE))
for name, src in H.DD_POS:
    try:
        out = A.neutralize(src)
        ok, why = healed(out, src)
        extra = ""
        if ENGINE and ok:
            bad, err = engine_check(src, out)
            if bad:
                ok, extra = False, " ｜ ★引擎：产出报错 %s" % err.splitlines()[-1][:34]
        note = why + extra
        shown = out.replace("\n", "\\n")
    except AssertionError as e:
        ok, note, shown = True, "响亮抛错（视为已中和）", "<抛错>"
    if not ok:
        reds.append(name)
    print("  正 %-24s %s ｜ %-26s ｜ %s" % ("✓" if ok else "✗", name, note, shown[:46]))
for name, src in H.DD_NEG:
    try:
        out = A.neutralize(src); ok = (out == src)
    except AssertionError:
        ok = False
    if not ok:
        reds.append(name)
    print("  负 %-24s %s" % ("✓" if ok else "✗", name))

print()
print("=== USE 面 14 格 · %s ===" % LABEL)
for name, src in USE_POS:
    try:
        out = A.neutralize(src); ok = ("qk_e2e" not in out)
    except AssertionError:
        ok = True
    if not ok:
        reds.append(name)
    print("  正 %-16s %s" % ("✓" if ok else "✗", name))
for name, src in USE_NEG:
    try:
        out = A.neutralize(src); ok = (out == src)
    except AssertionError:
        ok = False
    if not ok:
        reds.append(name)
    print("  负 %-16s %s" % ("✓" if ok else "✗", name))

print()
print("红格（%d）= %s" % (len(reds), reds or "无 ⇒ 全过 ✓"))
