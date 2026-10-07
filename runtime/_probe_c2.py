# -*- coding: utf-8 -*-
"""T23 取证：c2/collector 插件的路由 + 注册方式 + 谁本应匿名。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re

ROOT = USDT_ROOT + r"\02-backend-node\src_restored"

print("=== 1) app.js 的插件注册顺序 ===")
p = os.path.join(ROOT, "app.js")
if os.path.isfile(p):
    lines = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
    for i, l in enumerate(lines, 1):
        t = l.strip()
        if "register(" in t or "import " in t and "Plugin" in t:
            print("  %4d: %s" % (i, t[:118]))

print("")
print("=== 2) apiPlugin 的 authMiddleware 注册 ===")
p2 = os.path.join(ROOT, "plugins", "api", "index.js")
if os.path.isfile(p2):
    lines = io.open(p2, encoding="utf-8", errors="replace").read().splitlines()
    for i, l in enumerate(lines, 1):
        t = l.strip()
        if any(k in t for k in ["register", "authMiddleware", "import", "await"]):
            print("  %4d: %s" % (i, t[:118]))

print("")
print("=== 3) android 插件（修好的范本）===")
p3 = os.path.join(ROOT, "plugins", "android", "index.js")
if os.path.isfile(p3):
    lines = io.open(p3, encoding="utf-8", errors="replace").read().splitlines()
    for i, l in enumerate(lines, 1):
        t = l.strip()
        if any(k in t for k in ["register", "authMiddleware", "import", "await", "//"]):
            print("  %4d: %s" % (i, t[:118]))

print("")
print("=== 4) c2 插件的路由与注册 ===")
p4 = os.path.join(ROOT, "plugins", "c2", "index.js")
if os.path.isfile(p4):
    lines = io.open(p4, encoding="utf-8", errors="replace").read().splitlines()
    print("  c2/index.js 行数:", len(lines))
    for i, l in enumerate(lines, 1):
        t = l.strip()
        if any(k in t for k in ["register", "authMiddleware", "import", "await", "addHook"]):
            print("  %4d: %s" % (i, t[:118]))

print("")
print("=== 5) c2 与 collector 的全部路由 ===")
PAT = re.compile(r"""fastify\.(get|post|put|delete)\(\s*['"`]([^'"`]+)""")
for plug in ["c2", "collector"]:
    print("  --- plugins/%s ---" % plug)
    base = os.path.join(ROOT, "plugins", plug)
    for dp, dn, fns in os.walk(base):
        for f in fns:
            if not f.endswith(".js"):
                continue
            fp = os.path.join(dp, f)
            try:
                s = io.open(fp, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            for m in PAT.finditer(s):
                rel = os.path.relpath(fp, base)
                print("    %-34s %-6s %s" % (rel, m.group(1).upper(), m.group(2)))

print("")
print("=== 6) SKIP_AUTH_PATHS 当前白名单 ===")
p6 = os.path.join(ROOT, "plugins", "api", "middleware", "auth.js")
if os.path.isfile(p6):
    lines = io.open(p6, encoding="utf-8", errors="replace").read().splitlines()
    for i in range(15, min(30, len(lines))):
        t = lines[i].rstrip()
        if t.strip():
            print("  %4d: %s" % (i + 1, t[:125]))
