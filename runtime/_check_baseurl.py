# -*- coding: utf-8 -*-
"""查前端 baseURL 的实际值 + 代理连通性。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re
import urllib.request

print("=== 1) src/utils/request.js ===")
p = USDT_ROOT + r"\03-web-admin\src\utils\request.js"
s = io.open(p, encoding="utf-8", errors="replace").read()
for i, l in enumerate(s.splitlines(), 1):
    t = l.strip()
    if any(k in t for k in ["baseURL", "VITE_BASE_API", "import.meta.env", "timeout",
                            "withCredentials", "axios.create"]):
        print("  %4d: %s" % (i, t[:130]))

print("")
print("=== 2) .env.production 的值 ===")
for f in [".env.production", ".env"]:
    fp = os.path.join(USDT_ROOT + r"\03-web-admin", f)
    if os.path.isfile(fp):
        print("  --- %s ---" % f)
        for l in io.open(fp, encoding="utf-8", errors="replace").read().splitlines():
            if l.strip() and not l.strip().startswith("//"):
                print("    ", l.strip()[:110])

print("")
print("=== 3) dist 主包里 baseURL 的实际字面量 ===")
JS = USDT_ROOT + r"\03-web-admin\dist"
pat = re.compile(r"baseURL\s*:\s*([^,;}]{0,60})")
for dp, dn, fns in os.walk(JS):
    for f in fns:
        if not f.endswith(".js"):
            continue
        fp = os.path.join(dp, f)
        try:
            t = io.open(fp, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for m in pat.finditer(t):
            print("  %-52s %s" % (os.path.relpath(fp, JS), m.group(1)[:70]))

print("")
print("=== 4) 代理连通性 ===")
for u in ["http://127.0.0.1:8080/api/dashboard/collect-summary",
          "http://127.0.0.1:8080/api/dashboard/device-versions",
          "http://127.0.0.1:8080/api/dashboard/ttl-status"]:
    try:
        r = urllib.request.urlopen(u, timeout=15)
        body = r.read(160).decode("utf-8", "replace")
        print("  %s => %s  %s" % (u, r.status, body))
    except Exception as e:
        print("  %s => ERR %s" % (u, e))
