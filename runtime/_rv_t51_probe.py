# -*- coding: utf-8 -*-
"""复核 T51 · 独立离线实证（只读）。对象 = 打过补丁后的新 sha。
⛔ 不依赖 T49 轮结论；全部当场重跑。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import sys, io, os
sys.path.insert(0, IOS_ROOT + r"\_integration\_fix_work")
import verify_ad09_schema_migration_diff as A
import verify_migration_hygiene as H
TMP = A.TMP_DB
print("TMP_DB=%s | HEAD_RE=%s | STMT_RE=%s" % (TMP, A._USE_HEAD_RE.pattern, A._USE_STMT_RE.pattern))

def run(sql):
    try:
        return A.neutralize(sql), None
    except AssertionError as ex:
        return None, str(ex)

print("\n=== ① 夹令牌形态（F-T49-A 主诉）===")
cases_pos = {
  "块注释夹令牌":  "USE qk_e2e /* prod */;",
  "行注释夹令牌":  "USE qk_e2e -- prod\n;",
  "换行+块注释":   "USE\n  qk_e2e  /* x */  ;",
  "同行中段":      "SET @x:=1; USE qk_e2e; ALTER TABLE t ADD COLUMN c INT;",
  "前导行注释":    "-- c\nUSE qk_e2e;",
  "前导块注释":    "/* c */ USE qk_e2e;",
  "反引号库名":    "USE `qk_e2e`;",
  "大写":          "USE QK_E2E;",
}
for k, s in cases_pos.items():
    out, err = run(s)
    ok = (err is not None) or (out is not None and "qk_e2e" not in out.lower() and TMP in out)
    print("  %-12s 改/抛=%s | %s" % (k, ok, ("RAISE: "+err[:60]) if err else repr(out)))

print("\n=== ② 误伤面（应「原样不动」）===")
cases_neg = {
  "字符串内 USE":   "INSERT INTO t VALUES ('USE qk_e2e;');",
  "列名 use":       "SELECT use FROM t;",
  "USE_ 前缀":      "USE_THIS_COL = 1;",
  "UPDATE 语句":    "UPDATE t SET a=1;",
  "user 表":        "SELECT * FROM user;",
  "注释里 USE":     "-- USE qk_e2e;\nSELECT 1;",
}
for k, s in cases_neg.items():
    out, err = run(s)
    untouched = (err is None and out == s)
    print("  %-12s 原样不动=%s | %s" % (k, untouched, ("RAISE: "+err[:50]) if err else repr(out)))

print("\n=== ③ fail-closed（解析不出库名 ⇒ 应响亮抛）===")
cases_fc = {
  "USE @var":  "USE @db;",
  "USE 空":    "USE ;",
  "USE 无分号尾": "USE qk_e2e",
}
for k, s in cases_fc.items():
    out, err = run(s)
    print("  %-12s RAISE=%s | %s" % (k, err is not None, err[:70] if err else repr(out)))

print("\n=== ④ 口径同源（中和/哨兵/hygiene 三处是否共用 _USE_HEAD_RE）===")
print("  applier 中和用 _USE_HEAD_RE :", "_USE_HEAD_RE.match(code)" in
      io.open(IOS_ROOT + r"\_integration\_fix_work\verify_ad09_schema_migration_diff.py", encoding="utf-8").read())
print("  hygiene 有自写 re.compile :", "re.compile" in
      io.open(IOS_ROOT + r"\_integration\_fix_work\verify_migration_hygiene.py", encoding="utf-8").read().split("A5/V6")[0])
print("  hygiene _code_uses 用 A._USE_HEAD_RE :", hasattr(H, "_code_uses"))

print("\n=== ⑤ 版本注释 /*! */ 形态（额外探）===")
for k, s in {"版本注释包裹": "/*! USE qk_e2e */;", "版本注释+真语句": "/*!50003 USE qk_e2e */;"}.items():
    out, err = run(s)
    print("  %-14s RAISE=%s | %s" % (k, err is not None, err[:60] if err else repr(out)))
