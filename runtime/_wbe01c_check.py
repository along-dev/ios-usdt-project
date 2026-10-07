# -*- coding: utf-8 -*-
"""独立复核 WBE01-C 的核心断言：哪些判据脚本会对业务表做 DELETE/UPDATE。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import io
import os
import re

ROOT = IOS_ROOT + r"\_integration\_fix_work"

BIZ = ("bill", "wallet", "settlement", "machine", "token",
       "agent", "packet", "custom", "wallet_balance")

PAT_DEL = re.compile(r"DELETE\s+FROM\s+[`\"']?(%s)[`\"']?" % "|".join(BIZ), re.I)
PAT_UPD = re.compile(r"UPDATE\s+[`\"']?(%s)[`\"']?" % "|".join(BIZ), re.I)
# 也找裸的 DELETE FROM（不带表名白名单）
PAT_DEL_ANY = re.compile(r"DELETE\s+FROM\s+[`\"']?(\w+)", re.I)

print("=== ① 含业务表 DELETE/UPDATE 的判据脚本 ===")
hits = []
for f in sorted(os.listdir(ROOT)):
    if not f.endswith((".py", ".mjs", ".js")):
        continue
    if not (f.startswith("verify_") or f.startswith("_verify")):
        continue
    p = os.path.join(ROOT, f)
    try:
        s = io.open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        continue
    dels = PAT_DEL.findall(s) + PAT_DEL_ANY.findall(s)
    upds = PAT_UPD.findall(s)
    if dels or upds:
        hits.append((f, sorted(set(d.lower() for d in dels)),
                     sorted(set(u.lower() for u in upds))))

print("  命中: %d 个脚本" % len(hits))
print("")
for f, d, u in hits:
    print("  %-46s" % f)
    if d:
        print("      DELETE: %s" % ", ".join(d[:8]))
    if u:
        print("      UPDATE: %s" % ", ".join(u[:8]))

print("")
print("=== ② 是否产生【整表 DELETE FROM bill】 ===")
for f in sorted(os.listdir(ROOT)):
    if not f.endswith((".py", ".mjs", ".js")):
        continue
    p = os.path.join(ROOT, f)
    try:
        s = io.open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        continue
    for m in re.finditer(r"DELETE\s+FROM\s+[`\"']?bill[`\"']?\s*;", s, re.I):
        ln = s[:m.start()].count("\n") + 1
        print("  ★ %s:%d  %s" % (f, ln, m.group(0)[:60]))

print("")
print("=== ③ 库名指向（是否 qk_e2e） ===")
for f in sorted(os.listdir(ROOT)):
    if not f.endswith((".py", ".mjs", ".js")):
        continue
    p = os.path.join(ROOT, f)
    try:
        s = io.open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        continue
    if re.search(r"DELETE\s+FROM|UPDATE\s+", s, re.I) and "qk_e2e" in s:
        n = len(re.findall(r"qk_e2e", s))
        print("  %-46s qk_e2e 出现 %d 次" % (f, n))
