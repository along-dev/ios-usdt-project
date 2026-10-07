# -*- coding: utf-8 -*-
"""X3 取证：统计 verify_*.py 的编码设置情况。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import glob
import io
import os
import re

D = IOS_ROOT + r"\_integration\_fix_work"
files = sorted(glob.glob(os.path.join(D, "verify_*.py")))
print("verify_*.py 总数:", len(files))

no_enc = []
has_enc = []
for p in files:
    try:
        s = io.open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        continue
    if "PYTHONIOENCODING" in s or "reconfigure" in s:
        has_enc.append(os.path.basename(p))
    else:
        no_enc.append(os.path.basename(p))

print("已设编码:", len(has_enc))
print("未设编码:", len(no_enc))

# 未设编码中，含 ✓/✗ 等非 GBK 字符的（N3 的真实候选）
CHECK = "\u2713\u2717\u2192\u21d2\u2022\u25cf\u25b6\u2716\u26a0"
risky = []
for name in no_enc:
    p = os.path.join(D, name)
    try:
        s = io.open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        continue
    hits = [c for c in CHECK if c in s]
    if hits:
        risky.append((name, "".join(hits)))

print("")
print("★ 真正有崩溃风险（未设编码 + 含非 GBK 字符）:", len(risky))
for n, h in risky[:20]:
    print("   %-52s %s" % (n, h))

print("")
print("未设编码的前 15 个（无论是否含特殊字符）:")
for n in no_enc[:15]:
    print("   ", n)
