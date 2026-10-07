# -*- coding: utf-8 -*-
"""核实 sys_base_menus 引用的 component 是否在 dist 中有对应产物。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import json
import os
import subprocess

MYSQL = IOS_ROOT + r"\_integration\_fix_work\_toolchain\mariadb-11.4.4-winx64\bin\mysql.exe"
DIST = USDT_ROOT + r"\03-web-admin\dist"


def q(sql):
    r = subprocess.run([MYSQL, "-h", "127.0.0.1", "-P", "13306", "-u", "root", "qk_e2e",
                        "-N", "-B", "-e", sql], capture_output=True, text=True, timeout=30)
    return [l.split("\t") for l in r.stdout.strip().splitlines() if l.strip()]


print("=== 1) sys_base_menus 全部记录 ===")
rows = q("SELECT id, parent_id, path, name, component, title FROM sys_base_menus ORDER BY id")
for r in rows:
    print("  id=%-4s parent=%-4s path=%-14s name=%-16s comp=%s" %
          (r[0], r[1], r[2], r[3], r[4] if len(r) > 4 else ""))

print("")
print("=== 2) sys_authority_menus 关联 ===")
rows2 = q("SELECT sys_authority_authority_id, sys_base_menu_id FROM sys_authority_menus")
print("  关联数:", len(rows2))
from collections import Counter
c = Counter(r[0] for r in rows2)
for k, v in c.items():
    print("   authority=%s -> %d 个菜单" % (k, v))

print("")
print("=== 3) 判断前端组件是否存在 ===")
# 前端用 import.meta.glob('../view/**/*.vue') => dist 里每个 view 会打成一个 chunk
# 检查 dist/js 里是否有对应名字的 chunk
js_files = []
for dp, dn, fns in os.walk(DIST):
    for f in fns:
        if f.endswith(".js"):
            js_files.append(f)
print("  dist js 文件数:", len(js_files))

for r in rows:
    comp = r[4] if len(r) > 4 else ""
    if not comp:
        continue
    # view/dashboard/index.vue -> dashboard
    parts = comp.replace("view/", "").replace(".vue", "").split("/")
    key = parts[-1] if parts[-1] != "index" else (parts[-2] if len(parts) > 1 else parts[-1])
    hits = [f for f in js_files if key.lower() in f.lower()]
    status = "OK " if hits else "MISS"
    print("  [%s] %-46s key=%-16s (%d chunk)" % (status, comp, key, len(hits)))
    if hits:
        for h in hits[:2]:
            print("         %s" % h)
