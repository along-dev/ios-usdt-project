# -*- coding: utf-8 -*-
"""探针：04-landing 的 templates / assets 内容 + dashboard 里引用的全部资源。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re

ROOT = USDT_ROOT

print("=== 1) 04-landing/templates ===")
d = os.path.join(ROOT, "04-landing", "templates")
if os.path.isdir(d):
    for dp, dn, fns in os.walk(d):
        rel = os.path.relpath(dp, d)
        for f in sorted(fns)[:20]:
            print("  %-40s %8d B" % (os.path.join(rel, f), os.path.getsize(os.path.join(dp, f))))

print("")
print("=== 2) 04-landing/assets ===")
d = os.path.join(ROOT, "04-landing", "assets")
if os.path.isdir(d):
    for dp, dn, fns in os.walk(d):
        rel = os.path.relpath(dp, d)
        for f in sorted(fns)[:30]:
            print("  %-44s %8d B" % (os.path.join(rel, f), os.path.getsize(os.path.join(dp, f))))

print("")
print("=== 3) admin_dashboard.html 里引用的全部静态路径 ===")
P = os.path.join(ROOT, "03-web-admin", "static", "admin_dashboard.html")
s = io.open(P, encoding="utf-8", errors="replace").read()
paths = set()
for m in re.finditer(r"""["'](/[A-Za-z0-9_\-./]+\.(?:png|jpg|jpeg|gif|svg|webp|css|js))["']""", s):
    paths.add(m.group(1))
for m in re.finditer(r"""["'](/landing-pages/[^"']+)["']""", s):
    paths.add(m.group(1))
for p in sorted(paths):
    print("  ", p)
