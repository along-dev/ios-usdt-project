# -*- coding: utf-8 -*-
"""探针：gin-vue-admin 的 dist 部署配置（base / API 基址 / 入口）。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import json
import os
import re

ROOT = USDT_ROOT + r"\03-web-admin"

print("=== 1) vite.config.js 的 base / outDir / proxy ===")
p = os.path.join(ROOT, "vite.config.js")
s = io.open(p, encoding="utf-8", errors="replace").read()
for i, l in enumerate(s.splitlines(), 1):
    t = l.strip()
    if any(k in t for k in ("base:", "outDir:", "proxy", "target:", "port:", "VITE_BASE_API",
                            "define:", "loadEnv")):
        print("  %4d: %s" % (i, t[:118]))

print("")
print("=== 2) .env.* 文件 ===")
for f in sorted(os.listdir(ROOT)):
    if f.startswith(".env"):
        fp = os.path.join(ROOT, f)
        print("  --- %s ---" % f)
        for i, l in enumerate(io.open(fp, encoding="utf-8", errors="replace").read().splitlines(), 1):
            if l.strip() and not l.strip().startswith("#"):
                print("    %s" % l.strip()[:110])

print("")
print("=== 3) dist/index.html 的内容（看 base 与入口）===")
di = os.path.join(ROOT, "dist", "index.html")
if os.path.isfile(di):
    print(io.open(di, encoding="utf-8", errors="replace").read())
else:
    print("  [缺失]")

print("")
print("=== 4) dist 顶层 ===")
d = os.path.join(ROOT, "dist")
if os.path.isdir(d):
    for e in sorted(os.listdir(d)):
        fp = os.path.join(d, e)
        print("  %s %s" % ("[DIR]" if os.path.isdir(fp) else "%8d" % os.path.getsize(fp), e))
