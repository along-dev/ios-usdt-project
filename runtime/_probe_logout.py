# -*- coding: utf-8 -*-
"""实测 ${ADMIN}/logout 的确切行为（为 X2 的弱断言修正提供确切期望值）。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

API = "http://127.0.0.1:3000"
ADMIN = "/mgr-admin-8bcde2021d98"


class NR(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def req(method, path, body=None, token=None, follow=False, ctype=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(API + path, data=data, method=method)
    if ctype:
        r.add_header("Content-Type", ctype)
    elif data is not None:
        r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Cookie", "accessToken=" + token)
    try:
        if follow:
            with urllib.request.urlopen(r, timeout=10) as x:
                return x.status, x.read()[:160], dict(x.headers)
        op = urllib.request.build_opener(NR)
        with op.open(r, timeout=10) as x:
            return x.status, x.read()[:160], dict(x.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:160], dict(e.headers or {})
    except Exception as e:
        return -1, str(e).encode()[:160], {}


# 1) 登录取 token
st, b, h = req("POST", "/api/auth/login",
               body={"username": "admin", "password": "i1c3-e2e-admin"})
tok = None
m = re.search(rb'"accessToken"\s*:\s*"([^"]+)"', b)
if m:
    tok = m.group(1).decode()
if not tok:
    sc = str(h.get("Set-Cookie", ""))
    m2 = re.search(r"accessToken=([^;]+)", sc)
    if m2:
        tok = m2.group(1)
print("1) login: HTTP=%s  token=%s" % (st, "yes" if tok else "no"))

# 2) logout 带 token
st2, b2, h2 = req("GET", ADMIN + "/logout", token=tok, follow=False)
print("2) logout(带 token): HTTP=%s  Location=%s  body=%s"
      % (st2, h2.get("Location", ""), b2[:70]))

# 3) logout 无 token
st3, b3, h3 = req("GET", ADMIN + "/logout", token=None, follow=False)
print("3) logout(无 token): HTTP=%s  Location=%s  body=%s"
      % (st3, h3.get("Location", ""), b3[:70]))

# 4) logout 后原 token 是否失效
if tok:
    st4, b4, _ = req("GET", f"{ADMIN}/api/theme", token=tok, follow=False)
    print("4) logout 后用原 token 访问 /api/theme: HTTP=%s" % st4)

# 5) 读 admin.js 的 logout 实现（确证期望值来源）
p = USDT_ROOT + r"\02-backend-node\src_restored\plugins\android\admin.js"
lines = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
print("")
print("5) admin.js 的 logout 实现（:983-1015）:")
for i in range(982, min(1015, len(lines))):
    t = lines[i].rstrip()
    if t.strip():
        print("   %4d: %s" % (i + 1, t[:120]))
