# -*- coding: utf-8 -*-
"""X4 取证（续4）：读 dga_expansion.json 的 seed 与 32 域名。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import io
import json
import sys

P = IOS_ROOT + r"\recon\dga_expansion.json"
d = json.load(io.open(P, encoding="utf-8", errors="replace"))
print("顶层键:", list(d.keys()))
print("seeds:", json.dumps(d.get("seeds"), ensure_ascii=False))
print("live:", json.dumps(d.get("live"), ensure_ascii=False)[:200])

dbs = d.get("domains_by_seed")
print("")
print("domains_by_seed 类型:", type(dbs).__name__)
if isinstance(dbs, dict):
    for seed, doms in dbs.items():
        print("  seed =", seed)
        print("  domains 数 =", len(doms) if isinstance(doms, list) else doms)
        if isinstance(doms, list):
            for x in doms[:5]:
                print("     ", x)

# ★ 关键：用 dga.py 从该 seed 复算，与存储的 32 域名比对
print("")
print("=== 复算验证（用 recon/dga.py）===")
sys.path.insert(0, IOS_ROOT + r"\recon")
try:
    import dga
    for seed, doms in (dbs or {}).items():
        if not isinstance(doms, list) or not doms:
            continue
        # 存储的可能是 dict/字符串
        stored = []
        for x in doms:
            if isinstance(x, str):
                stored.append(x)
            elif isinstance(x, dict):
                stored.append(x.get("domain") or x.get("host") or str(x))
        calc = dga.gen(seed, len(stored) or 32)
        print("  seed=%s" % seed)
        print("    存储 %d 条，实算 %d 条" % (len(stored), len(calc)))
        print("    前3存储:", stored[:3])
        print("    前3实算:", calc[:3])
        same = (stored == calc)
        print("    ★ 逐项相同:", same)
        if not same:
            # 找差异
            diff = [(i, a, b) for i, (a, b) in enumerate(zip(stored, calc)) if a != b]
            print("    差异数:", len(diff), " 前3:", diff[:3])
except Exception as e:
    import traceback
    traceback.print_exc()
