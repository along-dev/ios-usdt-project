# -*- coding: utf-8 -*-
"""复核 T53 · 独立离线实证（只读）。对象 = 第三洞收口后的新 sha。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import sys
sys.path.insert(0, IOS_ROOT + r"\_integration\_fix_work")
import verify_ad09_schema_migration_diff as A
import verify_migration_hygiene as H
TMP = A.TMP_DB
print("TMP=%s" % TMP)

def run(sql):
    try:
        return A.neutralize(sql), None
    except AssertionError as ex:
        return None, str(ex)

def show(label, sql, expect):
    out, err = run(sql)
    if err:
        got = "RAISE"
    else:
        leaked = "qk_e2e" in out
        got = "改/抛" if (not leaked and TMP in out) else ("不动" if out == sql else "变了")
    mark = "OK " if got == expect else "★MISMATCH"
    print("  %-9s %-34s 期望=%-4s 实得=%-4s | %s"
          % (mark, label, expect, got, (err[:60] if err else repr(out))))

print("\n=== 卡的 V1 矩阵：8 正例（须改或抛）===")
P = [
 ("①行首",        "USE qk_e2e;", "改/抛"),
 ("②夹令牌块注",   "USE qk_e2e /* prod */;", "改/抛"),
 ("③版本注释",     "/*!32306 USE qk_e2e */;", "改/抛"),
 ("③b MariaDB版注", "/*M!100100 USE qk_e2e */;", "改/抛"),
 ("⑤同行中段",     "SET @x:=1; USE qk_e2e; ALTER TABLE t ADD COLUMN c INT;", "改/抛"),
 ("⑥大小写",       "use qk_e2e;", "改/抛"),
 ("⑦反引号",       "USE `qk_e2e`;", "改/抛"),
 ("⑧行尾注释",     "USE qk_e2e; -- prod", "改/抛"),
]
for l, s, e in P: show(l, s, e)

print("\n=== 卡的 V1 矩阵：6 负控（须原样不动）★ 记录件只列了 2 个 ===")
N = [
 ("④⑨字符串内",   "INSERT INTO t VALUES ('USE qk_e2e;');", "不动"),
 ("⑩列名 use",    "SELECT use FROM t;", "不动"),
 ("⑪USE_ 前缀",    "USE_THIS_COL = 1;", "不动"),
 ("⑫UPDATE",      "UPDATE t SET a=1;", "不动"),
 ("⑬user 表",      "SELECT * FROM user;", "不动"),
 ("⑭注释内",       "-- USE qk_e2e;\nSELECT 1;", "不动"),
]
for l, s, e in N: show(l, s, e)

print("\n=== 卡反向 + 边界探（派单 ①② 点名）===")
X = [
 ("普通块注释",     "/* USE qk_e2e */;", "不动"),
 ("版注-非USE",     "/*!50003 SET @x=1 */;", "不动"),
 ("dump 版注",      "/*!40101 SET NAMES utf8 */;", "不动"),
 ("版注-无版本号",   "/*! USE qk_e2e */;", "改/抛"),
 ("版注-多语句",     "/*!50003 USE qk_e2e; ALTER TABLE t ADD COLUMN c INT */;", "改/抛"),
 ("空体 /*!*/",     "/*!*/;", "不动"),
 ("空体+语句",       "/*!*/ SELECT 1;", "不动"),
 ("版注内 CREATE DB", "/*!50003 CREATE DATABASE foo */;", "?"),
 ("注释切开关键字",   "US/**/E qk_e2e;", "?"),
 ("标识符间注释",     "USE /**/ qk_e2e;", "改/抛"),
]
for l, s, e in X: show(l, s, e)

print("\n=== code_level_uses 计数（真实树应=4）===")
import os
MIG = USDT_ROOT + r"\07-db\migration"
tot = 0
for f in sorted(os.listdir(MIG)):
    if f.endswith(".sql"):
        raw = open(os.path.join(MIG, f), encoding="utf-8").read()
        tot += len(A.code_level_uses(raw))
print("  真实树 代码级 USE 总处数 =", tot)
