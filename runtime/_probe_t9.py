# -*- coding: utf-8 -*-
"""T9 取证：后台看板（4.3.1-4.3.3）的现状。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re

ROOT = USDT_ROOT

print("=== §4.3 后台完善需求 ===")
p = os.path.join(ROOT, "09-docs", "analysis", "需求文档.md")
lines = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
for i in range(161, min(172, len(lines))):
    t = lines[i].rstrip()
    if t.strip():
        print("  %4d: %s" % (i + 1, t[:140]))

print("")
print("=== 现有看板/统计类端点 ===")
R = os.path.join(ROOT, "02-backend-node", "src_restored", "plugins", "api", "routes")
PAT = re.compile(r"""fastify\.(get|post)\(\s*['"`]([^'"`]+)""")
KW = ["dashboard", "stats", "statistics", "devices", "visitors", "channel-stats"]
if os.path.isdir(R):
    for fn in sorted(os.listdir(R)):
        if not fn.endswith(".js"):
            continue
        t = io.open(os.path.join(R, fn), encoding="utf-8", errors="replace").read()
        for m in PAT.finditer(t):
            path = m.group(2)
            if any(k in path for k in KW):
                print("  %-24s %-6s %s" % (fn, m.group(1).upper(), path))

print("")
print("=== 前端 dashboard / 统计页面 ===")
V = os.path.join(ROOT, "03-web-admin", "src", "view")
for dp, dn, fns in os.walk(V):
    for fn in fns:
        if fn.endswith(".vue") and re.search(r"dashboard|statis|overview", fn, re.I):
            fp = os.path.join(dp, fn)
            print("  %8d B  %s" % (os.path.getsize(fp), os.path.relpath(fp, V)))

print("")
print("=== gasleak 的 18 个菜单（§5.1）===")
for i in range(188, min(200, len(lines))):
    t = lines[i].rstrip()
    if t.strip():
        print("  %4d: %s" % (i + 1, t[:150]))
