# -*- coding: utf-8 -*-
"""X6 取证（续2）：核实"分账"是否真的无端点（P-5：0 命中先怀疑量尺）。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re

ROOT = USDT_ROOT + r"\02-backend-node\src_restored"

# 1) 全仓搜"分账"相关语义（中英文 + 常见命名）
PATS = [
    r"settle", r"split", r"ratio", r"share", r"commission", r"payout",
    r"分账", r"分成", r"结算", r"佣金", r"revenue", r"profit",
    r"distribution", r"allocate", r"allocation",
]

print("=== 在 src_restored 全树搜'分账'语义 ===")
hits_by_pat = {}
for dp, dn, fns in os.walk(ROOT):
    dn[:] = [d for d in dn if d not in ("node_modules", ".git")]
    for fn in fns:
        if not fn.endswith(".js"):
            continue
        p = os.path.join(dp, fn)
        try:
            if os.path.getsize(p) > 4 * 1024 * 1024:
                continue
            s = io.open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for pat in PATS:
            n = len(re.findall(pat, s, re.I))
            if n:
                hits_by_pat.setdefault(pat, []).append((os.path.relpath(p, ROOT), n))

for pat in PATS:
    lst = hits_by_pat.get(pat, [])
    total = sum(n for _, n in lst)
    print("  %-16s 命中 %3d 次，分布 %d 个文件" % (pat, total, len(lst)))
    for f, n in sorted(lst, key=lambda x: -x[1])[:4]:
        print("      %-50s %d" % (f, n))

# 2) 模型层是否有"分账"相关 collection
print("")
print("=== 数据模型（models）中是否有分账相关 ===")
M = os.path.join(ROOT, "core", "db", "models")
if os.path.isdir(M):
    for fn in sorted(os.listdir(M)):
        if fn.endswith(".js"):
            print("   ", fn)
