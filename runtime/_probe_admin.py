# -*- coding: utf-8 -*-
"""列出 admin.js 的全部路由 + static 资源。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re

p = USDT_ROOT + r"\02-backend-node\src_restored\plugins\android\admin.js"
s = io.open(p, encoding="utf-8", errors="replace").read()
lines = s.splitlines()
print("  admin.js 行数:", len(lines))
print("")
print("  === 全部路由 ===")
PAT = re.compile(r"""fastify\.(get|post|put|delete)\(\s*['"`]([^'"`]+)""")
for i, l in enumerate(lines, 1):
    m = PAT.search(l)
    if m:
        print("    %4d  %-6s %s" % (i, m.group(1).upper(), m.group(2)))

print("")
print("  === ADMIN 常量与静态挂载 ===")
for i, l in enumerate(lines, 1):
    t = l.strip()
    if any(k in t for k in ("export const ADMIN", "resolveLoginHtmlPath", "resolveDashboard",
                            "sendFile", "readFileSync", "DASHBOARD")):
        print("    %4d  %s" % (i, t[:118]))

print("")
print("  === static 目录 ===")
sd = USDT_ROOT + r"\03-web-admin\static"
if os.path.isdir(sd):
    for f in sorted(os.listdir(sd)):
        fp = os.path.join(sd, f)
        if os.path.isfile(fp):
            print("    %8d B  %s" % (os.path.getsize(fp), f))

print("")
print("  === dist 目录 ===")
dd = USDT_ROOT + r"\03-web-admin\dist"
if os.path.isdir(dd):
    n = sum(len(f) for _, _, f in os.walk(dd))
    print("    文件数:", n)
    for e in sorted(os.listdir(dd)):
        print("      ", e)
