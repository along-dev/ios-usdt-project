# -*- coding: utf-8 -*-
"""X4 取证：从 mongo_records.json 找渠道 seed 与 domains。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import io
import json

P = IOS_ROOT + r"\recon\mongo_records.json"
d = json.load(io.open(P, encoding="utf-8", errors="replace"))
print("顶层键:", list(d.keys()))
cols = d.get("collections")
print("collections 类型:", type(cols).__name__)
if isinstance(cols, list):
    print("集合数:", len(cols))
    for c in cols[:20]:
        if isinstance(c, dict):
            print("   ", list(c.keys())[:6], " name=", c.get("name"), " n=", c.get("count") or c.get("n"))
elif isinstance(cols, dict):
    for k, v in list(cols.items())[:20]:
        n = len(v) if isinstance(v, list) else "?"
        print("   %-30s %s" % (k, n))

print("")
data = d.get("data")
print("data 类型:", type(data).__name__)
if isinstance(data, dict):
    for k, v in list(data.items())[:25]:
        n = len(v) if isinstance(v, list) else ("obj" if isinstance(v, dict) else v)
        print("   %-30s %s" % (k, n))
elif isinstance(data, list):
    print("data 条数:", len(data))
    for i, r in enumerate(data[:5]):
        if isinstance(r, dict):
            print("   [%d] keys=%s" % (i, list(r.keys())[:8]))
