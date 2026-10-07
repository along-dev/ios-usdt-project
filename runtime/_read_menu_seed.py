# -*- coding: utf-8 -*-
"""读 01-backend-go/source/system/menu.go 的原始 menu seed（判断应有的全貌）。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re

P = USDT_ROOT + r"\01-backend-go\source\system\menu.go"
s = io.open(P, encoding="utf-8", errors="replace").read()
lines = s.splitlines()
print("  menu.go 行数:", len(lines))
print("")
print("=== 全部 menu 条目 ===")
for i, l in enumerate(lines, 1):
    t = l.strip()
    if "SysBaseMenu{" in t or "Component:" in t:
        m = re.search(r'Path:\s*"([^"]*)".*?Name:\s*"([^"]*)".*?Component:\s*"([^"]*)"', t)
        if m:
            print("  %4d  path=%-18s name=%-18s comp=%s" % (i, m.group(1), m.group(2), m.group(3)))
        else:
            print("  %4d  %s" % (i, t[:130]))

print("")
print("=== 前端 api/ 目录（找真实接口）===")
A = USDT_ROOT + r"\03-web-admin\src\api"
for dp, dn, fns in os.walk(A):
    for f in sorted(fns):
        if f.endswith(".js"):
            print("  ", os.path.relpath(os.path.join(dp, f), A).replace("\\", "/"))
