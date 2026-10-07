# -*- coding: utf-8 -*-
"""验证每个菜单的 component 是否能在 dist 的 chunk 里找到（模拟 asyncRouter 的匹配）。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import os
import subprocess

MYSQL = IOS_ROOT + r"\_integration\_fix_work\_toolchain\mariadb-11.4.4-winx64\bin\mysql.exe"
ROOT = USDT_ROOT + r"\03-web-admin"
DIST = os.path.join(ROOT, "dist")


def q(sql):
    r = subprocess.run([MYSQL, "-h", "127.0.0.1", "-P", "13306", "-u", "root", "qk_e2e",
                        "-N", "-B", "--default-character-set=utf8mb4", "-e", sql],
                       capture_output=True, timeout=30)
    return [l.split("\t") for l in r.stdout.decode("utf-8", "replace").strip().splitlines() if l.strip()]


print("=== 1) 前端 src/view 下真实存在的 .vue ===")
V = os.path.join(ROOT, "src", "view")
src_set = set()
for dp, dn, fns in os.walk(V):
    for f in fns:
        if f.endswith(".vue"):
            rel = os.path.relpath(os.path.join(dp, f), V).replace("\\", "/")
            src_set.add("view/" + rel)
print("  src/view 共 %d 个 .vue" % len(src_set))

print("")
print("=== 2) 逐个菜单核对 component 是否存在于 src ===")
rows = q("SELECT id, parent_id, path, name, component, title FROM sys_base_menus ORDER BY parent_id, id")
ok = miss = 0
missed = []
for r in rows:
    comp = r[4] if len(r) > 4 else ""
    if not comp:
        continue
    base = comp  # 形如 view/xxx/yyy.vue
    # src 里可能不带 .vue 或用 index
    found = base in src_set
    if not found:
        # 尝试 view/xxx/yyy/index.vue
        alt = base.replace(".vue", "/index.vue")
        found = alt in src_set
    if found:
        ok += 1
        print("  [OK ] %-56s" % comp)
    else:
        miss += 1
        missed.append((r[0], r[2], comp))
        print("  [MISS] %-54s  (path=%s)" % (comp, r[2]))

print("")
print("  命中 %d / 缺失 %d" % (ok, miss))

print("")
print("=== 3) src 有但【菜单未引用】的页面 ===")
menu_comps = {r[4] for r in rows if len(r) > 4 and r[4]}
for s in sorted(src_set):
    if s.startswith("view/layout/") or s.startswith("view/error/") or s.endswith("routerHolder.vue"):
        continue
    if s not in menu_comps:
        print("  ", s)
