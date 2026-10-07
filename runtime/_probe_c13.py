# -*- coding: utf-8 -*-
"""T23 取证：载荷侧调用 c2 端点时带什么凭证？（决定 C-13 能否加鉴权）"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re

ROOT = USDT_ROOT

print("=== 1) c2 端点的处理代码：是否已有任何校验？ ===")
base = os.path.join(ROOT, "02-backend-node", "src_restored", "plugins", "c2", "routes")
for f in sorted(os.listdir(base)):
    if not f.endswith(".js"):
        continue
    p = os.path.join(base, f)
    s = io.open(p, encoding="utf-8", errors="replace").read()
    print("  --- %s (%d 行) ---" % (f, len(s.splitlines())))
    for i, l in enumerate(s.splitlines(), 1):
        t = l.strip()
        if any(k in t for k in ["headers", "token", "sign", "verify", "auth", "secret",
                                "hmac", "key", "check", "reject", "401"]):
            if len(t) > 4 and not t.startswith("//"):
                print("    %4d: %s" % (i, t[:118]))

print("")
print("=== 2) 载荷侧（05-ios / 06-android）调用时带什么 header？ ===")
PAT = re.compile(r"""(headers?|X-[A-Za-z-]+|Authorization|sign|hmac)[^\n]{0,80}""", re.I)
for sub in ["05-ios", "06-android", "11-payment"]:
    d = os.path.join(ROOT, sub)
    if not os.path.isdir(d):
        continue
    hits = 0
    for dp, dn, fns in os.walk(d):
        dn[:] = [x for x in dn if x not in (".git", "node_modules", "__pycache__")]
        for f in fns:
            if not f.endswith((".js", ".py", ".html", ".json")):
                continue
            fp = os.path.join(dp, f)
            try:
                s = io.open(fp, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            if any(k in s for k in ["/taskget", "/taskresult", "/ip-sync", "/a'", '/u"', "/t'"]):
                hits += 1
                if hits <= 3:
                    print("  [%s] %s" % (sub, os.path.relpath(fp, ROOT)))
                    for i, l in enumerate(s.splitlines(), 1):
                        tl = l.strip()
                        if any(k in tl for k in ["taskget", "taskresult", "ip-sync", "headers", "X-", "sign"]):
                            print("      %4d: %s" % (i, tl[:110]))
    print("  [%s] 含 c2 端点的文件数: %d" % (sub, hits))

print("")
print("=== 3) 现有 c2 路由的完整内容（挑 taskget 看）===")
p = os.path.join(base, "task.js")
if os.path.isfile(p):
    lines = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
    print("  task.js 行数:", len(lines))
    for i, l in enumerate(lines[:60], 1):
        print("    %4d: %s" % (i, l.rstrip()[:118]))
