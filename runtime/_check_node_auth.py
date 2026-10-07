# -*- coding: utf-8 -*-
"""核实 Node 3000 的鉴权机制（cookie 名 / 校验方式）+ gin-vue-admin 的 token 是否兼容。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re

ROOT = USDT_ROOT + r"\02-backend-node\src_restored"

print("=== 1) 3000 的 auth middleware ===")
P = os.path.join(ROOT, "middleware", "auth.js")
if os.path.isfile(P):
    lines = io.open(P, encoding="utf-8", errors="replace").read().splitlines()
    for i, l in enumerate(lines, 1):
        t = l.strip()
        if any(k in t for k in ["cookie", "Cookie", "accessToken", "jwt", "verify",
                                "SKIP_AUTH", "401", "未授权", "token"]):
            print("  %4d: %s" % (i, t[:120]))
else:
    print("  [缺失]")

print("")
print("=== 2) 登录端点 ===")
for dp, dn, fns in os.walk(ROOT):
    dn[:] = [d for d in dn if d not in ("node_modules", ".git")]
    for f in fns:
        if not f.endswith(".js"):
            continue
        fp = os.path.join(dp, f)
        try:
            s = io.open(fp, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if "/auth/login" in s or "'auth/login'" in s:
            print("  %s" % os.path.relpath(fp, ROOT))
            for i, l in enumerate(s.splitlines(), 1):
                if "login" in l.lower() and ("fastify" in l or "post" in l.lower()):
                    print("    %4d: %s" % (i, l.strip()[:110]))

print("")
print("=== 3) 全部 /api 路由（3000）===")
PAT = re.compile(r"""fastify\.(get|post|put|delete)\(\s*['"`]([^'"`]+)""")
for dp, dn, fns in os.walk(ROOT):
    dn[:] = [d for d in dn if d not in ("node_modules", ".git")]
    for f in fns:
        if not f.endswith(".js"):
            continue
        fp = os.path.join(dp, f)
        try:
            s = io.open(fp, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for m in PAT.finditer(s):
            p = m.group(2)
            if "/api/" in p and ("auth" in p or "login" in p or "dashboard" in p):
                print("  %-40s %s" % (os.path.relpath(fp, ROOT), p))
