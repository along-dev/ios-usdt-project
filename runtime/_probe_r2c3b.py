# -*- coding: utf-8 -*-
"""R2-C3 深查：三个目录的内容是否被【生产运行时】依赖。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib
import io
import os
import re

BASE = USDT_ROOT + r"\02-backend-node"
DIRS = [".verify_tmp_storage", ".verify_tmp_storage_ds", ".rt_storage"]

print("=== 1) 三个目录的内容是否与【产物内的同名文件】一致 ===")
for d in DIRS:
    root = os.path.join(BASE, d)
    if not os.path.isdir(root):
        print("  %s: 不存在" % d)
        continue
    print("  --- %s ---" % d)
    for dp, dn, fns in os.walk(root):
        for fn in fns:
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, root)
            # 在产物内找同名文件
            cands = []
            for sub in ("payloads", "templates", "static", "public"):
                c = os.path.join(BASE, sub, rel)
                if os.path.isfile(c):
                    cands.append(c)
            same = []
            for c in cands:
                h1 = hashlib.sha256(open(p, "rb").read()).hexdigest()
                h2 = hashlib.sha256(open(c, "rb").read()).hexdigest()
                same.append((os.path.relpath(c, BASE), h1 == h2))
            print("    %-42s %8d B  产物内同名: %s"
                  % (rel, os.path.getsize(p), same if same else "无"))

print("")
print("=== 2) src_restored 是否引用这些目录名 ===")
SR = os.path.join(BASE, "src_restored")
found = False
for dp, dn, fns in os.walk(SR):
    dn[:] = [d for d in dn if d not in ("node_modules", ".git")]
    for fn in fns:
        p = os.path.join(dp, fn)
        if not fn.endswith((".js", ".mjs", ".cjs", ".json")):
            continue
        try:
            s = io.open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for d in DIRS:
            if d in s:
                print("  ★ %s 引用 %s" % (os.path.relpath(p, BASE), d))
                found = True
if not found:
    print("  ✓ src_restored 中【无任何】引用")

print("")
print("=== 3) 产物根是否已有 payloads 目录（对比用）===")
for sub in ("payloads", "templates"):
    p = os.path.join(BASE, sub)
    if os.path.isdir(p):
        n = sum(len(f) for _, _, f in os.walk(p))
        print("  %-12s 存在，%d 个文件" % (sub, n))
    else:
        print("  %-12s 不存在" % sub)
