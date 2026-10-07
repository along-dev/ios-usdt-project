# -*- coding: utf-8 -*-
"""X6 取证：从 admin_dashboard.html 提取端点，定位 1.8 的"5 类核心操作"。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re

P = USDT_ROOT + r"\03-web-admin\static\admin_dashboard.html"
s = io.open(P, encoding="utf-8", errors="replace").read()

# 提取 ADMIN + "..." 形式的端点
eps = set()
for m in re.finditer(r"""ADMIN\s*\+\s*["']([^"']+)""", s):
    eps.add(m.group(1))

print("=== admin_dashboard.html 中的端点（ADMIN + ...）===")
for e in sorted(eps):
    print("  ", e)

print("")
print("=== 5 类核心操作候选 ===")
KW = [("channel", "渠道"), ("device", "设备"), ("wallet", "钱包"),
      ("collect", "归集"), ("settle", "分账"), ("user", "用户"), ("order", "订单")]
for kw, name in KW:
    hits = sorted(e for e in eps if kw in e.lower())
    print("  %-4s %s" % (name, hits if hits else "（dashboard 中未找到）"))

# 再从 plugins/api/routes 枚举实际注册的端点
print("")
print("=== plugins/api/routes/*.js 注册的路由（前 40）===")
R = USDT_ROOT + r"\02-backend-node\src_restored\plugins\api\routes"
routes = []
if os.path.isdir(R):
    for fn in sorted(os.listdir(R)):
        if not fn.endswith(".js"):
            continue
        t = io.open(os.path.join(R, fn), encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"""fastify\.(get|post|put|delete)\(\s*['"`]([^'"`]+)""", t):
            routes.append((fn, m.group(1).upper(), m.group(2)))
for fn, meth, path in routes[:40]:
    print("  %-22s %-6s %s" % (fn, meth, path))
print("  ... 共 %d 条" % len(routes))

print("")
print("=== plugins/android/*.js 的路由 ===")
A = USDT_ROOT + r"\02-backend-node\src_restored\plugins\android"
if os.path.isdir(A):
    for fn in sorted(os.listdir(A)):
        if not fn.endswith(".js"):
            continue
        t = io.open(os.path.join(A, fn), encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"""fastify\.(get|post)\(\s*['"`]([^'"`]+)""", t):
            print("  %-14s %-6s %s" % (fn, m.group(1).upper(), m.group(2)))
