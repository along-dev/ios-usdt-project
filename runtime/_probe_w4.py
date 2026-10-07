# -*- coding: utf-8 -*-
"""波次 4 剩余项取证：T10（AES 密钥/依赖）+ T16（vue-qrcode/多副本/bsc）+ T11（R-07）。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re

ROOT = USDT_ROOT


def walk_js(base, exts=(".js", ".py", ".json", ".vue", ".ps1", ".go")):
    for dp, dn, fns in os.walk(base):
        dn[:] = [d for d in dn if d not in ("node_modules", ".git", "__pycache__", "dist")]
        for fn in fns:
            if fn.endswith(exts):
                yield os.path.join(dp, fn)


print("=== T16-1: vue-qrcode 依赖 ===")
pkg = os.path.join(ROOT, "03-web-admin", "package.json")
if os.path.isfile(pkg):
    s = io.open(pkg, encoding="utf-8", errors="replace").read()
    for i, l in enumerate(s.splitlines(), 1):
        if "qrcode" in l.lower():
            print("  package.json:%d  %s" % (i, l.strip()))
    # 全 src 搜引用
    hits = 0
    for fp in walk_js(os.path.join(ROOT, "03-web-admin", "src")):
        try:
            t = io.open(fp, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if "qrcode" in t.lower():
            hits += 1
            print("    [引用] %s" % os.path.relpath(fp, ROOT))
    print("  src 树内引用数: %d" % hits)

print("")
print("=== T16-2: 多副本域切换（P2-7）===")
for fp in walk_js(os.path.join(ROOT, "02-backend-node", "src_restored")):
    try:
        t = io.open(fp, encoding="utf-8", errors="replace").read()
    except Exception:
        continue
    if "region" in t and ("switch" in t.lower() or "副本" in t):
        rel = os.path.relpath(fp, ROOT)
        n = len(re.findall(r"region", t))
        print("  %-72s %d 命中" % (rel, n))

print("")
print("=== T16-3: bsc collector（§5.2.4）===")
for fp in walk_js(os.path.join(ROOT, "02-backend-node", "src_restored")):
    try:
        t = io.open(fp, encoding="utf-8", errors="replace").read()
    except Exception:
        continue
    if "bsc" in t.lower() and ("collector" in t.lower() or "collect" in t.lower()):
        rel = os.path.relpath(fp, ROOT)
        for i, l in enumerate(t.splitlines(), 1):
            if "bsc" in l.lower() and "collect" in l.lower():
                print("  %s:%d  %s" % (rel, i, l.strip()[:110]))

print("")
print("=== T10: AES 密钥（R-06 的 5/6）===")
for base, pat in [
    (os.path.join(ROOT, "06-android", "tools"), r"AES|KEY|IV\s*="),
    (os.path.join(ROOT, "05-ios"), r"AES|aesKey|decrypt"),
]:
    for fp in walk_js(base, (".py", ".js")):
        try:
            t = io.open(fp, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        m = re.findall(pat, t)
        if m:
            rel = os.path.relpath(fp, ROOT)
            print("  %-72s %d 命中" % (rel, len(m)))

print("")
print("=== T11: R-07 group.html:242 ===")
g = os.path.join(ROOT, "05-ios", "coruna", "group.html")
if os.path.isfile(g):
    lines = io.open(g, encoding="utf-8", errors="replace").read().splitlines()
    for i in range(238, min(246, len(lines))):
        print("  %4d: %s" % (i + 1, lines[i].strip()[:130]))
