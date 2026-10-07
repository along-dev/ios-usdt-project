# -*- coding: utf-8 -*-
"""看 T19 的两个看板页实际请求什么 URL。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os

V = USDT_ROOT + r"\03-web-admin\src\view\dashboard"
A = USDT_ROOT + r"\03-web-admin\src\api"

print("=== 1) deviceVersions.vue 的请求 ===")
p = os.path.join(V, "deviceVersions", "deviceVersions.vue")
if os.path.isfile(p):
    for i, l in enumerate(io.open(p, encoding="utf-8", errors="replace").read().splitlines(), 1):
        t = l.strip()
        if any(k in t for k in ("import", "request", "api", "url", "get(", "$get", "axios")):
            print("  %4d: %s" % (i, t[:120]))
else:
    print("  [缺失]")

print("")
print("=== 2) collectSummary.vue 的请求 ===")
p2 = os.path.join(V, "collectSummary", "collectSummary.vue")
if os.path.isfile(p2):
    for i, l in enumerate(io.open(p2, encoding="utf-8", errors="replace").read().splitlines(), 1):
        t = l.strip()
        if any(k in t for k in ("import", "request", "api", "url", "get(", "$get", "axios")):
            print("  %4d: %s" % (i, t[:120]))
else:
    print("  [缺失]")

print("")
print("=== 3) src/api/dashboard.js 的内容 ===")
p3 = os.path.join(A, "dashboard.js")
if os.path.isfile(p3):
    for i, l in enumerate(io.open(p3, encoding="utf-8", errors="replace").read().splitlines(), 1):
        print("  %4d: %s" % (i, l.rstrip()[:120]))
else:
    print("  [缺失]")

print("")
print("=== 4) dist 里实际打的包（确认 chunk 是否含新 path）===")
import re
JS = USDT_ROOT + r"\03-web-admin\dist\js"
for f in sorted(os.listdir(JS)):
    if "collectSummary" in f and not "legacy" in f:
        s = io.open(os.path.join(JS, f), encoding="utf-8", errors="replace").read()
        print("  %s (%d B)" % (f, len(s)))
        for m in re.finditer(r"[\"'`]([^\"'`]*dashboard[^\"'`]*)[\"'`]", s):
            print("     url:", m.group(1))
