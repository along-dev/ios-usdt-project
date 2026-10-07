# -*- coding: utf-8 -*-
"""核实：C2 命令的下发通道（决定 S6 能否在 group.html 侧实现）。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re

BASE = USDT_ROOT + r"\05-ios\coruna"
PATS = ["processC2Commands", "c2Heartbeat", "c2Poll", "c2Ack", "c2HandleAdminCommand"]

for dp, dn, fns in os.walk(BASE):
    dn[:] = [d for d in dn if d not in (".git",)]
    for fn in fns:
        if not fn.endswith((".js", ".html")):
            continue
        p = os.path.join(dp, fn)
        try:
            if os.path.getsize(p) > 8 * 1024 * 1024:
                continue
            s = io.open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        hits = []
        for pat in PATS:
            c = len(re.findall(re.escape(pat), s))
            if c:
                hits.append("%s=%d" % (pat, c))
        if hits:
            print("  %-40s %s" % (os.path.relpath(p, BASE), "  ".join(hits)))

print("")
print("=== 其他可能下发 C2 命令的位置（02-backend-node 的 C2 端点）===")
B2 = USDT_ROOT + r"\02-backend-node\src_restored"
for dp, dn, fns in os.walk(B2):
    dn[:] = [d for d in dn if d not in ("node_modules", ".git")]
    for fn in fns:
        if not fn.endswith(".js"):
            continue
        p = os.path.join(dp, fn)
        try:
            s = io.open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if "c2" in s.lower() and re.search(r"(cmd|command)", s):
            n = len(re.findall(r"cmd", s))
            if n > 2:
                print("  %-50s cmd命中=%d" % (os.path.relpath(p, B2), n))
