# -*- coding: utf-8 -*-
"""R3-1 后续 · 4 个假红脚本的期望值取证（只读，不改）。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import io
import os
import re

ROOT = IOS_ROOT + r"\_integration\_fix_work"

TARGETS = [
    ("verify_d2c2_templates_consistency.py", ["darksword", "== 5", "= 5", "5（契约", "20 个"]),
    ("verify_t19_dashboards.py", ["limitation", "None", "== None", "total"]),
    ("verify_t21_previews.py", ["app.js", "UNCHANGED", "CHANGED", "冻结"]),
    ("verify_f1c10_bridge_e2e.mjs", ["QIANKE_API_BASE", "QIANKE_SERVICE_TOKEN", "bridgeEnabled"]),
]

for fname, kws in TARGETS:
    p = os.path.join(ROOT, fname)
    if not os.path.isfile(p):
        print("=== %s === [缺失]" % fname)
        continue
    lines = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
    print("=== %s (%d 行) ===" % (fname, len(lines)))
    for i, l in enumerate(lines, 1):
        t = l.rstrip()
        if any(k in t for k in kws) and t.strip() and not t.strip().startswith("#"):
            print("  %4d: %s" % (i, t[:126]))
    print("")
