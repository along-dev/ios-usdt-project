# -*- coding: utf-8 -*-
"""核对每个菜单页面的 .vue 引用的 API，是否在 Go 侧真实存在。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re
import subprocess

ROOT = USDT_ROOT
V = os.path.join(ROOT, "03-web-admin", "src", "view")
API = os.path.join(ROOT, "03-web-admin", "src", "api")
GO = os.path.join(ROOT, "01-backend-go")

MYSQL = IOS_ROOT + r"\_integration\_fix_work\_toolchain\mariadb-11.4.4-winx64\bin\mysql.exe"


def q(sql):
    r = subprocess.run([MYSQL, "-h", "127.0.0.1", "-P", "13306", "-u", "root", "qk_e2e",
                        "-N", "-B", "--default-character-set=utf8mb4", "-e", sql],
                       capture_output=True, timeout=30)
    return [l.split("\t") for l in r.stdout.decode("utf-8", "replace").strip().splitlines() if l.strip()]


print("=== 1) 菜单清单 ===")
rows = q("SELECT id, parent_id, path, name, component, title FROM sys_base_menus ORDER BY parent_id, sort")
for r in rows:
    comp = r[4] if len(r) > 4 else ""
    print("  %-4s %-4s %-24s %-30s %s" % (r[0], r[1], r[2], r[3], comp))

print("")
print("=== 2) src/api 里的所有 request URL ===")
urls = set()
for dp, dn, fns in os.walk(API):
    for f in fns:
        if not f.endswith(".js"):
            continue
        s = io.open(os.path.join(dp, f), encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"""url:\s*['"`]([^'"`]+)""", s):
            urls.add(m.group(1))
        for m in re.finditer(r"""(?:get|post|put|delete)\(\s*['"`]([^'"`]+)""", s):
            urls.add(m.group(1))
print("  共 %d 个 URL" % len(urls))
for u in sorted(urls):
    print("   ", u)
