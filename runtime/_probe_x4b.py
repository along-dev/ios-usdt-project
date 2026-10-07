# -*- coding: utf-8 -*-
"""X4 取证（续）：列出 collections 的结构与 channels 数据。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import io
import json

P = IOS_ROOT + r"\recon\mongo_records.json"
d = json.load(io.open(P, encoding="utf-8", errors="replace"))
cols = d["collections"]
print("=== collections（%d 个）===" % len(cols))
for i, c in enumerate(cols):
    if isinstance(c, dict):
        print("  [%d] %s" % (i, json.dumps(c, ensure_ascii=False)[:150]))
    else:
        print("  [%d] %r" % (i, str(c)[:100]))

print("")
data = d["data"]
print("=== data（%d 条）===" % len(data))
for i, r in enumerate(data):
    if isinstance(r, dict) and r:
        print("  [%d] keys=%s" % (i, list(r.keys())[:10]))
    else:
        print("  [%d] %r" % (i, str(r)[:80]))
