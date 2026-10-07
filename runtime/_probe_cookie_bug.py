# -*- coding: utf-8 -*-
"""排查同族脚本：http() 是否用 dict(r.headers) 折叠了 Set-Cookie。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import glob
import io
import os
import re

D = IOS_ROOT + r"\_integration\_fix_work"
files = sorted(glob.glob(os.path.join(D, "verify_*.py")))

RISKY = []
OK = []
for p in files:
    base = os.path.basename(p)
    try:
        s = io.open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        continue
    # 是否消费 Set-Cookie
    uses_ck = ("Set-Cookie" in s) or ("accessToken" in s and "Cookie" in s)
    # 是否用 dict(r.headers) / dict(e.headers)
    folds = bool(re.search(r"dict\(\s*[re]\.headers", s))
    # 是否已用 get_all
    uses_getall = "get_all(" in s
    if uses_ck:
        if folds and not uses_getall:
            RISKY.append(base)
        else:
            OK.append(base)

print("verify_*.py 总数:", len(files))
print("")
print("★ 依赖 Set-Cookie 且【折叠重名头】的脚本（须修）：", len(RISKY))
for f in RISKY:
    print("   ", f)
print("")
print("✓ 依赖 Set-Cookie 且【已正确处理】的脚本：", len(OK))
for f in OK:
    print("   ", f)
