# -*- coding: utf-8 -*-
"""R2-2 准备：从 Go 路由表导出 sys_apis 清单。

★ Owner 裁决 A：888 → 全部；9528 → 只读子集；不建 1234。
★ 本脚本【只读】：只导出路由，不写 DB。
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re
import json

ROOT = USDT_ROOT + r"\01-backend-go"
ROUTER = os.path.join(ROOT, "router")

# 1) 收集「分组变量 -> 前缀」
group_prefix = {}
PAT_GROUP = re.compile(r'(\w+)\s*:=\s*(?:\w+\.)?Group\(\s*"([^"]*)"\s*\)')
PAT_ASSIGN = re.compile(r'(\w+)\s*:=\s*(\w+)')

# 2) 收集路由：var.METHOD("path", handler)
PAT_ROUTE = re.compile(r'(\w+)\.(GET|POST|PUT|DELETE|PATCH)\(\s*"([^"]*)"')

# 3) 收集函数入参：func (x *T) InitXxxRouter(Router *gin.RouterGroup)
PAT_FUNC = re.compile(r'func\s+\([^)]*\)\s+(\w+)\(\s*(\w+)\s+\*gin\.RouterGroup\s*\)')

routes = []

for dp, dn, fns in os.walk(ROUTER):
    for f in sorted(fns):
        if not f.endswith(".go"):
            continue
        p = os.path.join(dp, f)
        rel = os.path.relpath(p, ROOT)
        lines = io.open(p, encoding="utf-8", errors="replace").read().splitlines()

        cur_fn = None
        param_name = None
        local = {}

        for l in lines:
            t = l.strip()
            if t.startswith("//") or not t:
                continue

            m = PAT_FUNC.search(t)
            if m:
                cur_fn = m.group(1)
                param_name = m.group(2)
                local = {}
                continue

            # 分组
            m = PAT_GROUP.search(t)
            if m:
                var, prefix = m.group(1), m.group(2)
                # 若前缀以 Router 入参为基，则拼上；否则独立
                local[var] = prefix
                continue

            # 路由
            m = PAT_ROUTE.search(t)
            if m:
                var, method, path = m.group(1), m.group(2), m.group(3)
                if var == param_name:
                    prefix = ""
                else:
                    prefix = local.get(var, None)
                if prefix is None:
                    # 该 var 不在本函数内定义（外部传入）⇒ 记 raw
                    prefix = f"<{var}>"
                full = "/" + "/".join(x for x in [prefix, path] if x)
                full = re.sub(r"/+", "/", full)
                routes.append({
                    "file": rel,
                    "func": cur_fn or "",
                    "group": prefix,
                    "method": method,
                    "path": path,
                    "full": full,
                })

print("=== 导出结果 ===")
print("  路由条数:", len(routes))
print("")

by_group = {}
for r in routes:
    by_group.setdefault(r["group"], []).append(r)

for g in sorted(by_group):
    print("  --- 分组 %r (%d 条) ---" % (g, len(by_group[g])))
    for r in by_group[g][:6]:
        print("    %-6s %s" % (r["method"], r["full"]))
    if len(by_group[g]) > 6:
        print("    ... 其余 %d 条" % (len(by_group[g]) - 6))

print("")
print("=== 写 JSON（供 R2-2 用）===")
out = IOS_ROOT + r"\_integration\_fix_work\_r22_routes.json"
with open(out, "w", encoding="utf-8") as fh:
    json.dump(routes, fh, ensure_ascii=False, indent=2)
print("  已写:", out)
