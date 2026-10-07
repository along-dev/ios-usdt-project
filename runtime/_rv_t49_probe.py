# -*- coding: utf-8 -*-
"""复核 T49 · 离线实证（只读）—— 不改受审件、不连库。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io, os, sys
HERE = IOS_ROOT + r"\_integration\_fix_work"
sys.path.insert(0, HERE)
MIG = USDT_ROOT + r"\07-db\migration"
import verify_ad09_schema_migration_diff as A
TMP = A.TMP_DB
print("TMP_DB =", TMP, "| _USE_ANCHOR =", A._USE_ANCHOR)

V1 = "SET @x:=1; USE qk_e2e; ALTER TABLE t ADD COLUMN c INT;"
out = A.neutralize(V1)
print("\n[V1 负控] in :", V1)
print("[V1 负控] out:", out)
print("[V1] 原库名消失 =", "qk_e2e" not in out, "| 指向临时库 =", TMP in out)

saved = A._USE_ANCHOR
A._USE_ANCHOR = "line"
out_line = A.neutralize(V1)
A._USE_ANCHOR = saved
print("\n[V1 反向 anchor=line] out:", out_line)
print("[V1 反向] 旧口径漏过(仍含 qk_e2e) =", "qk_e2e" in out_line)

# V2 正控：4 件与「旧口径逐字节一致」
four = ["50-custom-ownership.sql", "50-custom-ownership-rollback.sql",
        "51-customusdtnum-agentusdtnum-backfill.sql",
        "51-customusdtnum-agentusdtnum-backfill-rollback.sql"]
print("\n[V2 正控] 4 件逐字节对照：")
for f in four:
    raw = io.open(os.path.join(MIG, f), encoding="utf-8").read()
    neut = A.neutralize(raw)
    same = neut == raw.replace("USE qk_e2e;", "USE `%s`;" % TMP)
    print("   %-52s changed=%s bytesame=%s" % (f, neut != raw, same))

# 全 12 件：哪些被动过
names = sorted(f for f in os.listdir(MIG) if f.endswith(".sql"))
changed = [f for f in names if A.neutralize(io.open(os.path.join(MIG, f), encoding="utf-8").read())
           != io.open(os.path.join(MIG, f), encoding="utf-8").read()]
print("\n[全 %d 件] neutralize 改动件 = %s" % (len(names), changed))

# ★ 探洞：装置未覆盖的 USE 形态
print("\n[探洞] 非行首 / 变体形态：")
holes = {
    "同行中段(已知F-T48-A)": "SET @x:=1; USE qk_e2e; ALTER TABLE t ADD COLUMN c INT;",
    "内联块注释":            "USE qk_e2e /* c */;",
    "内联行注释":            "USE qk_e2e -- c\n;",
    "换行+内联注释":          "USE\n  qk_e2e  /* x */  ;",
    "注释后接语句":           "/*! SET x=1 */ USE qk_e2e;",
}
for label, sql in holes.items():
    try:
        r = A.neutralize(sql)
        leaked = "qk_e2e" in r
        print("   %-22s 漏=%s | out=%r" % (label, leaked, r))
    except AssertionError as ex:
        print("   %-22s 哨兵抛错=%s" % (label, ex))
