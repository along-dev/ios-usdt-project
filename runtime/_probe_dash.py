# -*- coding: utf-8 -*-
"""探针：admin_dashboard.html 的"落地页预览"实现。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import re

P = USDT_ROOT + r"\03-web-admin\static\admin_dashboard.html"
s = io.open(P, encoding="utf-8", errors="replace").read()
lines = s.splitlines()
print("  总行数:", len(lines))
print("")

print("=== 1) iframe / 预览 / 模板 相关行 ===")
PAT = re.compile(r"iframe|preview|template|vodex|landing|src\s*=|<img|qr", re.I)
for i, l in enumerate(lines, 1):
    if PAT.search(l):
        t = l.strip()
        if t and not t.startswith("//"):
            print("  %4d: %s" % (i, t[:130]))

print("")
print("=== 2) 所有 fetch/请求 URL ===")
PAT2 = re.compile(r"""fetch\(|axios|XMLHttpRequest|url\s*=|\$\.(get|post)""", re.I)
for i, l in enumerate(lines, 1):
    if PAT2.search(l):
        t = l.strip()
        print("  %4d: %s" % (i, t[:130]))

print("")
print("=== 3) ADMIN 常量 ===")
for i, l in enumerate(lines, 1):
    if "const ADMIN" in l or "ADMIN =" in l:
        print("  %4d: %s" % (i, l.strip()[:130]))
