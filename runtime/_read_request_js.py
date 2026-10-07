# -*- coding: utf-8 -*-
"""读 request.js 的响应拦截器，确定 res 的真实结构。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io

P = USDT_ROOT + r"\03-web-admin\src\utils\request.js"
s = io.open(P, encoding="utf-8", errors="replace").read()
lines = s.splitlines()
print("  request.js 行数:", len(lines))
print("")
for i, l in enumerate(lines, 1):
    print("  %4d: %s" % (i, l.rstrip()[:126]))
