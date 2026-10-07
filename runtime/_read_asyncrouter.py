# -*- coding: utf-8 -*-
"""读 asyncRouter.js —— 看 component 字符串如何解析成真实组件。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os

P = USDT_ROOT + r"\03-web-admin\src\utils\asyncRouter.js"
s = io.open(P, encoding="utf-8", errors="replace").read()
lines = s.splitlines()
print("  asyncRouter.js 行数:", len(lines))
print("")
for i, l in enumerate(lines, 1):
    print("  %4d: %s" % (i, l.rstrip()[:128]))
