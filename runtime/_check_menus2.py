# -*- coding: utf-8 -*-
"""核实菜单引用的 component 是否在 dist 中有产物（修正编码）。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import os
import subprocess

MYSQL = IOS_ROOT + r"\_integration\_fix_work\_toolchain\mariadb-11.4.4-winx64\bin\mysql.exe"
DIST = USDT_ROOT + r"\03-web-admin\dist"


def q(sql):
    r = subprocess.run([MYSQL, "-h", "127.0.0.1", "-P", "13306", "-u", "root", "qk_e2e",
                        "-N", "-B", "--default-character-set=utf8mb4", "-e", sql],
                       capture_output=True, timeout=30)
    out = r.stdout.decode("utf-8", "replace")
    return [l.split("\t") for l in out.strip().splitlines() if l.strip()]


print("=== 1) sys_base_menus ===")
rows = q("SELECT id, parent_id, path, name, component, title FROM sys_base_menus ORDER BY id")
for r in rows:
    comp = r[4] if len(r) > 4 else ""
    print("  id=%-4s parent=%-4s path=%-16s comp=%s" % (r[0], r[1], r[2], comp))

print("")
print("=== 2) 全部 view/*.vue 的清单（从 src 读，判断 dist 是否有）===")
V = USDT_ROOT + r"\03-web-admin\src\view"
vues = []
for dp, dn, fns in os.walk(V):
    for f in fns:
        if f.endswith(".vue"):
            vues.append(os.path.relpath(os.path.join(dp, f), V).replace("\\", "/"))
print("  src/view 下 .vue 共 %d 个" % len(vues))
for v in sorted(vues):
    print("   ", v)

print("")
print("=== 3) dist/js 的 chunk 名单（与 view 对应）===")
JS = os.path.join(DIST, "js")
if os.path.isdir(JS):
    fs = sorted(os.listdir(JS))
    print("  共 %d 个" % len(fs))
    for f in fs:
        print("   ", f)
