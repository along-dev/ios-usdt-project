# -*- coding: utf-8 -*-
"""T24 取证：Node 管理台的 RBAC 现状。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os

ROOT = USDT_ROOT + r"\02-backend-node\src_restored"

print("=== 1) auth.js 的 RBAC 逻辑 ===")
p = os.path.join(ROOT, "plugins", "api", "middleware", "auth.js")
lines = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
print("  行数:", len(lines))
for i, l in enumerate(lines, 1):
    print("  %4d: %s" % (i, l.rstrip()[:124]))
