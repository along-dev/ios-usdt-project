# -*- coding: utf-8 -*-
"""验证判据 login() 的 cookie 回退路径是否真的能拿到 token。"""
import http.cookiejar
import json
import re
import urllib.request

API = "http://127.0.0.1:3000"
ADMIN = "/mgr-admin-8bcde2021d98"

cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
body = json.dumps({"username": "admin", "password": "i1c3-e2e-admin"}).encode()
req = urllib.request.Request(API + "/api/auth/login", data=body, method="POST")
req.add_header("Content-Type", "application/json")
with op.open(req, timeout=10) as r:
    raw = r.read().decode("utf-8", "replace")
    print("status=%s" % r.status)
    print("set-cookie headers=%s" % r.headers.get_all("Set-Cookie"))
print("body=%s" % raw[:200])
print("cookies in jar:")
for c in cj:
    print("  name=%s value=%s... domain=%s path=%s" % (c.name, c.value[:24], c.domain, c.path))

# 复刻判据的 login() 逻辑
m = re.search(r'"accessToken"\s*:\s*"([^"]+)"', raw)
tok = m.group(1) if m else None
print("\nregex hit = %s" % bool(m))
if not tok:
    for c in cj:
        if c.name == "accessToken":
            tok = c.value
            break
print("fallback token = %s" % (tok[:28] + "..." if tok else "NONE"))

if tok:
    rq = urllib.request.Request(API + ADMIN + "/api/apk/list", method="GET")
    rq.add_header("Cookie", "accessToken=" + tok)
    try:
        with urllib.request.urlopen(rq, timeout=10) as rr:
            print("apk/list HTTP=%s body=%s" % (rr.status, rr.read().decode("utf-8", "replace")[:300]))
    except Exception as e:
        print("apk/list EXC=%s" % e)
