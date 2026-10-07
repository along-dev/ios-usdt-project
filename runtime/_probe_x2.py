# -*- coding: utf-8 -*-
"""X2 取证：找判据中的弱断言（!==404、硬编码 True）。"""
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

# 1) 弱断言模式
PATTERNS = [
    (r"!=\s*404", "`!= 404`（只要不是 404 就算过）"),
    (r"!==\s*404", "`!== 404`"),
    (r"st\s*!=\s*404", "状态码 `!= 404`"),
    (r"rec\([^)]*,\s*True\s*,", "硬编码 True 的 rec(...)"),
    (r"assert\s+True", "`assert True`"),
    (r"in\s*\(\s*200\s*,\s*404\s*\)", "`in (200, 404)`（过宽）"),
    (r"st\s*in\s*\(200,\s*400\)", "`in (200, 400)`（过宽）"),
    (r"or\s+st\s*==\s*404", "允许 404 也算过"),
    (r"status\s*!=\s*404", "status != 404"),
]

hits = {}
for p in files:
    try:
        s = io.open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        continue
    lines = s.splitlines()
    for pat, desc in PATTERNS:
        for i, l in enumerate(lines, 1):
            if re.search(pat, l):
                hits.setdefault(desc, []).append(
                    (os.path.basename(p), i, l.strip()[:100]))

print("")
for desc, lst in hits.items():
    print("=== %s（%d 处）===" % (desc, len(lst)))
    for f, i, l in lst[:8]:
        print("  %-40s :%d  %s" % (f, i, l))
    if len(lst) > 8:
        print("  ... 还有 %d 处" % (len(lst) - 8))
    print("")
