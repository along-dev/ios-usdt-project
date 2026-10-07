# -*- coding: utf-8 -*-
"""完整核对：前端 119 个 API URL vs Go 侧真实路由。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re

ROOT = USDT_ROOT
API = os.path.join(ROOT, "03-web-admin", "src", "api")
GO = os.path.join(ROOT, "01-backend-go")

# 1) 收集前端 URL
urls = set()
for dp, dn, fns in os.walk(API):
    for f in fns:
        if not f.endswith(".js"):
            continue
        s = io.open(os.path.join(dp, f), encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"""url:\s*['"`]([^'"`]+)""", s):
            urls.add(m.group(1))
        for m in re.finditer(r"""\b(?:get|post|put|delete)\(\s*['"`]([^'"`]+)""", s):
            urls.add(m.group(1))

# 2) 收集 Go 路由
goroutes = set()
PAT = re.compile(r'\.(GET|POST|PUT|DELETE)\(\s*"([^"]+)"')
for dp, dn, fns in os.walk(GO):
    dn[:] = [d for d in dn if d not in (".git", "node_modules")]
    for f in fns:
        if not f.endswith(".go"):
            continue
        s = io.open(os.path.join(dp, f), encoding="utf-8", errors="replace").read()
        for m in PAT.finditer(s):
            goroutes.add(m.group(2))
# 也收 Router.Group 的前缀
prefixes = set()
for dp, dn, fns in os.walk(GO):
    dn[:] = [d for d in dn if d not in (".git", "node_modules")]
    for f in fns:
        if not f.endswith(".go"):
            continue
        s = io.open(os.path.join(dp, f), encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"""Group\(\s*"([^"]*)"\)""", s):
            prefixes.add(m.group(1))

print("=== 前端 URL 数: %d ===" % len(urls))
print("=== Go 路由数: %d ===" % len(goroutes))
print("=== Go Group 前缀: %s ===" % sorted(x for x in prefixes if x)[:30])
print("")

# 3) 逐个核对：前端 url 去掉 /api 前缀后，是否形如 <prefix>/<route>
hit, miss = 0, 0
misses = []
for u in sorted(urls):
    core = u
    if core.startswith("/api/"):
        core = core[5:]
    elif core.startswith("/api"):
        core = core[4:]
    # 在 goroutes 里找：route 是 core 的最后一段，或 core 以某 prefix 开头
    parts = [p for p in core.split("/") if p]
    last = parts[-1] if parts else core
    found = any(last == r for r in goroutes)
    if found:
        hit += 1
    else:
        miss += 1
        misses.append(u)

print("=== 结果 ===")
print("  命中: %d" % hit)
print("  缺失: %d" % miss)
print("")
print("=== 缺失清单 ===")
for u in misses:
    print("  ", u)
