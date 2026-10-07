# -*- coding: utf-8 -*-
"""X4 取证（续3）：找 DGA 判据的可用输入（seed + 32 domains）。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import io
import json
import os

R = IOS_ROOT + r"\recon"
print("=== recon 下与 DGA/域名相关的文件 ===")
for fn in sorted(os.listdir(R)):
    p = os.path.join(R, fn)
    if not os.path.isfile(p):
        continue
    if any(k in fn.lower() for k in ("dga", "domain", "task2")):
        print("  %-28s %8d B" % (fn, os.path.getsize(p)))

print("")
for fn in ("dga_expansion.json", "domains15.json"):
    p = os.path.join(R, fn)
    if not os.path.isfile(p):
        continue
    print("=== %s ===" % fn)
    try:
        d = json.load(io.open(p, encoding="utf-8", errors="replace"))
        if isinstance(d, dict):
            for k, v in list(d.items())[:8]:
                n = len(v) if isinstance(v, (list, dict)) else v
                print("  %-24s %s" % (k, str(n)[:120]))
            # 打印前几个域名
            for k, v in d.items():
                if isinstance(v, list) and v:
                    print("  样例:", v[:3])
                    break
        elif isinstance(d, list):
            print("  条数:", len(d), " 样例:", d[:3])
    except Exception as e:
        print("  解析失败:", e)
    print("")

# task2_dga_expand.py 的输入来源
p = os.path.join(R, "task2_dga_expand.py")
if os.path.isfile(p):
    print("=== task2_dga_expand.py（找 seed 来源）===")
    s = io.open(p, encoding="utf-8", errors="replace").read()
    for i, l in enumerate(s.splitlines(), 1):
        if any(k in l for k in ("seed", "code", "mongo", "json", "open(", "load")):
            print("  %3d: %s" % (i, l.strip()[:120]))
