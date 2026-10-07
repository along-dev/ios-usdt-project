# -*- coding: utf-8 -*-
"""X6 取证（续）：在 plugins/api/routes 的 97 条路由中定位 1.8 的 5 类核心操作。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re

R = USDT_ROOT + r"\02-backend-node\src_restored\plugins\api\routes"
routes = []
for fn in sorted(os.listdir(R)):
    if not fn.endswith(".js"):
        continue
    t = io.open(os.path.join(R, fn), encoding="utf-8", errors="replace").read()
    for m in re.finditer(r"""fastify\.(get|post|put|delete)\(\s*['"`]([^'"`]+)""", t):
        routes.append((fn, m.group(1).upper(), m.group(2)))

print("总路由数:", len(routes))
print("")

# 1.8 的 5 类
KW = [
    ("渠道", ["channel"]),
    ("设备", ["device", "machine", "ua", "visitor", "visit"]),
    ("钱包", ["wallet", "address", "custom", "tatum", "chain"]),
    ("归集", ["collect"]),
    ("分账", ["settle", "split", "ratio", "share", "order"]),
]

for name, kws in KW:
    hits = [(fn, m, p) for fn, m, p in routes
            if any(k in p.lower() for k in kws)]
    print("=== %s（%d 条）===" % (name, len(hits)))
    for fn, m, p in hits[:12]:
        print("  %-22s %-6s %s" % (fn, m, p))
    if len(hits) > 12:
        print("  ... 还有 %d 条" % (len(hits) - 12))
    print("")

# 全部路由按文件分组（供参考）
print("=== 全部路由（按文件）===")
by_file = {}
for fn, m, p in routes:
    by_file.setdefault(fn, []).append((m, p))
for fn in sorted(by_file):
    print("  %-24s %d 条" % (fn, len(by_file[fn])))
