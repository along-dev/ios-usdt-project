# -*- coding: utf-8 -*-
"""复核 T49 · 第二组离线实证：A2 覆盖面 & 装置对『含尾随令牌的 USE 语句』的盲区。只读。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import sys
sys.path.insert(0, IOS_ROOT + r"\_integration\_fix_work")
import verify_ad09_schema_migration_diff as A
import verify_migration_hygiene as H

TMP = A.TMP_DB
print("H._code_uses 用的判定 =", H.A._USE_STMT_RE.pattern)
print("H 是否另写分句器 =", hasattr(H, "_iter_statements") or hasattr(H, "neutralize"))

cases = {
    "A 纯行首(真实形态)":       "USE qk_e2e;",
    "B 同行中段(F-T48-A已修)":  "SET @x:=1; USE qk_e2e; ALTER TABLE t ADD COLUMN c INT;",
    "C 块注释在分号前":          "USE qk_e2e /* prod */;",
    "D 行注释在分号前":          "USE qk_e2e -- prod\n;",
    "E 换行+块注释在分号前":      "USE\n  qk_e2e  /* x */  ;",
    "F 字符串内含USE(应放行)":    "INSERT INTO t VALUES ('USE qk_e2e;');",
    "G 字符串分号+真USE尾":       "INSERT INTO t VALUES ('a;b'); USE qk_e2e;",
}
print("\n%-26s | neutralize改写 | 哨兵抛错 | A2(_code_uses)计数 | A2残留检出" % "形态")
for label, sql in cases.items():
    try:
        out = A.neutralize(sql); err = "-"
    except AssertionError as ex:
        out, err = "", "YES"
    rewritten = (out != "" and "qk_e2e" not in out and TMP in out) if err == "-" else True
    cnt = H._code_uses(sql)
    try:
        resid = [d for d in H._code_uses(out) if d != TMP] if err == "-" else ["哨兵已抛"]
    except AssertionError:
        resid = ["哨兵已抛"]
    print("%-26s | %-12s | %-8s | %-22s | %s"
          % (label, rewritten, err, cnt, resid if resid else "无"))
