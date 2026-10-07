# -*- coding: utf-8 -*-
"""查 dist 的 gva 产物与 index.html 引用。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import datetime
import io
import os
import re

d = USDT_ROOT + r"\03-web-admin\dist"
n = sum(len(f) for _, _, f in os.walk(d))
print("  dist 文件数:", n)
print("  dist mtime:", datetime.datetime.fromtimestamp(os.path.getmtime(d)))
print("")

g = os.path.join(d, "gva")
if os.path.isdir(g):
    print("  --- dist/gva ---")
    for f in sorted(os.listdir(g)):
        p = os.path.join(g, f)
        print("    %s  %8d B  %s" % (datetime.datetime.fromtimestamp(os.path.getmtime(p)),
                                     os.path.getsize(p), f))

print("")
ix = os.path.join(d, "index.html")
if os.path.isfile(ix):
    s = io.open(ix, encoding="utf-8", errors="replace").read()
    print("  index.html 引用:")
    for m in re.finditer(r'(?:src|href)="([^"]+)"', s):
        print("   ", m.group(1))
else:
    print("  ★ index.html 不存在")

print("")
print("  --- dist 顶层 ---")
for e in sorted(os.listdir(d)):
    p = os.path.join(d, e)
    print("    %s %s" % ("[DIR]" if os.path.isdir(p) else "FILE ", e))
