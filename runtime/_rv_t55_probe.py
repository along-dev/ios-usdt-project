# -*- coding: utf-8 -*-
"""复核 T55 · 独立离线实证（只读）：DD 面矩阵 ＋ 未覆盖形态 ＋ 用 A6 自身判据回判。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import sys
sys.path.insert(0, IOS_ROOT + r"\_integration\_fix_work")
import verify_ad09_schema_migration_diff as A
import verify_migration_hygiene as H

def run(s):
    try: return A.neutralize(s), None
    except AssertionError as ex: return None, str(ex)

def show(label, src):
    out, err = run(src)
    if err:
        print("  %-26s RAISE: %s" % (label, err[:60])); return
    a6 = H._dd_healed(out, src)          # ★ 用 A6 自己的判据回判
    print("  %-26s A6判=%s | %r" % (label, "过✓" if a6 else "★不过", out))

print("=== 1) 记录的 DD 矩阵（应 7 正全过 / 4 负原样）===")
for n, s in H.DD_POS: print("  正", end=""); show(n, s)
for n, s in H.DD_NEG: print("  负", end=""); show(n, s)

print("\n=== 2) ★ 探未覆盖形态：DDL 关键字与 DATABASE 之间夹 trivia ===")
for n, s in [
    ("CREATE/**/DATABASE x;",        "CREATE/**/DATABASE x;"),
    ("CREATE /*c*/ DATABASE x;",     "CREATE /*c*/ DATABASE x;"),
    ("DROP/**/DATABASE x;",          "DROP/**/DATABASE x;"),
    ("版注内夹注释",                  "/*!50000 DROP/**/DATABASE x */;"),
    ("版注内 CREATE 夹注释",           "/*!50000 CREATE /*c*/ DATABASE x */;"),
]:
    show(n, s)

print("\n=== 3) 其它 DDL 同义词 / 形态（记录件 §七-3 自陈未纳）===")
for n, s in [
    ("CREATE SCHEMA x;",   "CREATE SCHEMA x;"),
    ("DROP SCHEMA x;",     "DROP SCHEMA x;"),
    ("小写 create database", "create database x;"),
    ("换行分隔（无 trivia）", "DROP\nDATABASE x;"),
    ("版注 版本号不可执行",  "/*!99999 DROP DATABASE x */;"),
    ("一条版注内两条 DDL",   "/*!50000 DROP DATABASE x; DROP DATABASE y */;"),
]:
    show(n, s)

print("\n=== 4) 外壳保全逐字节核（F-T53-A 主诉）===")
src = "/*!50000 DROP DATABASE x */;"
out, _ = run(src)
print("   in :", repr(src))
print("   out:", repr(out))
print("   收尾 */ 在:", "*/" in out, "| 未闭合 /*! 在:", ("/*!" in out and "*/" in out))
EOF_MARK = None
