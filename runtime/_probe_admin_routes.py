# -*- coding: utf-8 -*-
"""列出 admin.js 的全部路由注册及其所属导出函数。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import re

P = USDT_ROOT + r"\02-backend-node\src_restored\plugins\android\admin.js"
lines = io.open(P, encoding="utf-8", errors="replace").read().splitlines()

cur = "(top)"
print("=== 全部路由注册（含所属函数）===")
for i, l in enumerate(lines, 1):
    m = re.search(r"export async function (\w+)", l)
    if m:
        cur = m.group(1)
    m2 = re.search(r"""fastify\.(get|post|put|delete)\(\s*['"`]([^'"`]+)""", l)
    if m2:
        print("%4d: [%-16s] %-6s %s" % (i, cur, m2.group(1).upper(), m2.group(2)))

print("")
print("=== 函数边界 ===")
for i, l in enumerate(lines, 1):
    if re.search(r"export async function|^}", l):
        print("%4d: %s" % (i, l.strip()[:100]))
