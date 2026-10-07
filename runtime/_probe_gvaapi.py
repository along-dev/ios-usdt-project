# -*- coding: utf-8 -*-
"""探针：Go 侧 gin-vue-admin 的路由前缀（/api 的挂载）。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re

R = USDT_ROOT + r"\01-backend-go"

print("=== 1) initialize/router.go 的 RouterGroup ===")
p = os.path.join(R, "initialize", "router.go")
if os.path.isfile(p):
    s = io.open(p, encoding="utf-8", errors="replace").read()
    for i, l in enumerate(s.splitlines(), 1):
        t = l.strip()
        if any(k in t for k in ("Group(", "RouterGroup", "PublicGroup", "PrivateGroup",
                                "prefix", "Prefix")):
            print("  %4d: %s" % (i, t[:120]))
else:
    print("  [缺失]")

print("")
print("=== 2) config.yaml 的 system.router-prefix ===")
for cfg in [IOS_ROOT + r"\_integration\_fix_work\_i2c1_ws\config.yaml",
            USDT_ROOT + r"\01-backend-go\config.yaml"]:
    if os.path.isfile(cfg):
        print("  --- %s ---" % cfg)
        lines = io.open(cfg, encoding="utf-8", errors="replace").read().splitlines()
        for i, l in enumerate(lines, 1):
            if any(k in l for k in ("router-prefix", "prefix", "addr", "port", "db-name")):
                print("    %4d: %s" % (i, l.strip()[:110]))

print("")
print("=== 3) router/system 的 routerGroup 传入方式（抽样 enter.go / index）===")
for f in ["router/enter.go", "router/system/enter.go", "router/system/sys_base.go"]:
    fp = os.path.join(R, *f.split("/"))
    if os.path.isfile(fp):
        s = io.open(fp, encoding="utf-8", errors="replace").read()
        print("  --- %s ---" % f)
        for i, l in enumerate(s.splitlines(), 1):
            t = l.strip()
            if any(k in t for k in ("Group(", "RouterGroup", "func Init", "ApiGroup")):
                print("    %4d: %s" % (i, t[:118]))
