# -*- coding: utf-8 -*-
"""核实 34 个 /landing-pages/ 引用能否在产物内找到对应文件。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re

ROOT = USDT_ROOT

# 1) 取 dashboard 引用的全部 /landing-pages/ 路径
s = io.open(os.path.join(ROOT, "03-web-admin", "static", "admin_dashboard.html"),
            encoding="utf-8", errors="replace").read()
refs = sorted(set(re.findall(r"/landing-pages/[A-Za-z0-9_./\-]+\.(?:png|jpg|jpeg|webp|gif|svg|css|js)",
                             s)))
print("=== 引用总数: %d ===" % len(refs))

# 2) 建一个磁盘索引：把 04-landing 下所有文件按 basename 与 扁平化名 建索引
index = {}
for base in [os.path.join(ROOT, "04-landing")]:
    for dp, dn, fns in os.walk(base):
        dn[:] = [d for d in dn if d not in (".git", "node_modules")]
        for f in fns:
            fp = os.path.join(dp, f)
            rel = os.path.relpath(fp, base).replace("\\", "/")
            index.setdefault(f, []).append(rel)
            # 扁平化形式：a__b__c
            index.setdefault(rel.replace("/", "__"), []).append(rel)

print("  磁盘索引条目: %d" % len(index))
print("")

print("=== 逐个引用核对 ===")
hit, miss = 0, 0
for r in refs:
    # /landing-pages/<name>/static/...  ->  <name>__static__...
    flat = r[len("/landing-pages/"):].replace("/", "__")
    base = os.path.basename(r)
    cands = index.get(flat, []) + index.get(base, [])
    if cands:
        hit += 1
        print("  [OK ] %-58s <= %s" % (r[:58], cands[0]))
    else:
        miss += 1
        print("  [MISS] %s" % r)
print("")
print("  命中: %d   缺失: %d" % (hit, miss))
