# -*- coding: utf-8 -*-
"""定位 gin-vue-admin 验证码的实现与存储位置。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re

root = USDT_ROOT + r"\01-backend-go"

print("=== 1) baseApi.Captcha 的实现 ===")
for dp, dn, fns in os.walk(root):
    dn[:] = [d for d in dn if d not in (".git", "node_modules")]
    for fn in fns:
        if not fn.endswith(".go"):
            continue
        p = os.path.join(dp, fn)
        try:
            s = io.open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if "func (baseApi *BaseApi) Captcha" in s or "oc.OpenCaptcha" in s.lower():
            rel = os.path.relpath(p, root)
            lines = s.splitlines()
            for i, l in enumerate(lines, 1):
                if "func (baseApi *BaseApi) Captcha" in l or "OpenCaptcha" in l:
                    print("  === %s:%d ===" % (rel, i))
                    for j in range(i - 1, min(i + 60, len(lines))):
                        t = lines[j].rstrip()
                        if t.strip():
                            print("   %4d: %s" % (j + 1, t[:118]))
                    break

print("")
print("=== 2) utils 里的 captcha 包 ===")
u = os.path.join(root, "utils", "captcha.go")
if os.path.isfile(u):
    s = io.open(u, encoding="utf-8", errors="replace").read()
    for i, l in enumerate(s.splitlines(), 1):
        t = l.strip()
        if any(k in t for k in ("func ", "Store", "NewStore", "Redis", "Memory", "Verify")):
            print("  %4d: %s" % (i, t[:118]))
