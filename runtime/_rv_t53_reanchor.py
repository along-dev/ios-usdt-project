# -*- coding: utf-8 -*-
"""复核 T53 重锚 · 逐格重跑「记录件新矩阵」的 14 格（用记录件的<原样>字符串）。只读。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import sys
sys.path.insert(0, IOS_ROOT + r"\_integration\_fix_work")
import verify_ad09_schema_migration_diff as A
TMP = A.TMP_DB

def run(sql):
    try: return A.neutralize(sql), None
    except AssertionError as ex: return None, str(ex)

def cell(label, sql, expect):
    out, err = run(sql)
    if err: got = "RAISE"
    else:
        got = "改" if (out != sql and TMP in out and "qk_e2e" not in out) else ("不动" if out == sql else "变了")
    mark = "OK " if got == expect else "★差异"
    print("  %-6s %-16s 期望=%-3s 实得=%-3s | %s" % (mark, label, expect, got, (err[:50] if err else repr(out))))

print("== 正例 8（须「改」）==")
P = [
 ("P1","USE qk_e2e /* prod */;","改"),
 ("P2","USE qk_e2e -- prod\n;","改"),
 ("P3","USE qk_e2e\n/* prod */;","改"),
 ("P4","SET @x:=1; USE qk_e2e; ALTER TABLE t ADD COLUMN c INT;","改"),
 ("P5","-- lead\n/* lead */\nUSE qk_e2e;","改"),
 ("P6","USE `qk_e2e`;","改"),
 ("P7","USE QK_E2E;","改"),
 ("P8","/*!32306 USE qk_e2e */;","改"),
]
for l,s,e in P: cell(l,s,e)

print("== 负控 6（须「不动」）==")
N = [
 ("N1","INSERT INTO t VALUES ('USE qk_e2e;');","不动"),
 ("N2","SELECT `use` FROM t;","不动"),
 ("N3","USE_DB_X = 1;","不动"),
 ("N4","UPDATE t SET a = 1;","不动"),
 ("N5","SELECT user FROM t;","不动"),
 ("N6","/* USE qk_e2e */;","不动"),
]
for l,s,e in N: cell(l,s,e)
