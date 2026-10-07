# -*- coding: utf-8 -*-
"""探针：admin.js / api/index.js 的静态挂载能力 + 04-landing 资产完整清单。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re

ROOT = USDT_ROOT

print("=== 1) admin.js 全部 fastify 相关调用（找静态挂载）===")
p = os.path.join(ROOT, "02-backend-node", "src_restored", "plugins", "android", "admin.js")
lines = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
for i, l in enumerate(lines, 1):
    t = l.strip()
    if re.search(r"fastify\.\w+|register|static|sendFile|createReadStream|reply\.(type|send)", t):
        print("  %4d: %s" % (i, t[:120]))

print("")
print("=== 2) 全 Node 侧是否有 @fastify/static ===")
node_root = os.path.join(ROOT, "02-backend-node")
for dp, dn, fns in os.walk(node_root):
    dn[:] = [d for d in dn if d not in ("node_modules", ".git")]
    for fn in fns:
        if not fn.endswith(".js"):
            continue
        fp = os.path.join(dp, fn)
        try:
            s = io.open(fp, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if "fastify/static" in s or "fastifyStatic" in s:
            print("  %s" % os.path.relpath(fp, node_root))

print("")
print("=== 3) 04-landing/assets 的完整清单（按模板聚合）===")
A = os.path.join(ROOT, "04-landing", "assets")
if os.path.isdir(A):
    from collections import Counter
    c = Counter()
    for f in os.listdir(A):
        m = re.match(r"landing-pages__([^_]+)__static__", f)
        c[m.group(1) if m else "(其他)"] += 1
    for k, v in sorted(c.items()):
        print("  %-16s %d 文件" % (k, v))
    print("  合计:", sum(c.values()))

print("")
print("=== 4) 04-landing/templates 的完整清单 ===")
T = os.path.join(ROOT, "04-landing", "templates")
if os.path.isdir(T):
    fs = sorted(os.listdir(T))
    print("  共 %d 个" % len(fs))
    print("  " + ", ".join(fs[:60]))
