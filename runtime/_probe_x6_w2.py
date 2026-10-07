# -*- coding: utf-8 -*-
"""诊断 X6 的 W2：表单 POST ${ADMIN}/login 为何 404。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

API = "http://127.0.0.1:3000"
ADMIN = "/mgr-admin-8bcde2021d98"


def post(path, data, ctype, timeout=12):
    req = urllib.request.Request(API + path, data=data, method="POST")
    req.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()[:200], dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:200], dict(e.headers or {})
    except Exception as e:
        return -1, str(e).encode(), {}


print("=== 1) 表单 POST（urlencoded）===")
form = urllib.parse.urlencode({"username": "admin", "password": "i1c3-e2e-admin"}).encode()
st, b, h = post(f"{ADMIN}/login", form, "application/x-www-form-urlencoded")
print(f"  HTTP={st}  body={b.decode('utf-8','replace')[:150]}")
print(f"  Set-Cookie={h.get('Set-Cookie', '(无)')[:120]}")

print("")
print("=== 2) JSON POST ${ADMIN}/login ===")
import json as _j
st2, b2, h2 = post(f"{ADMIN}/login", _j.dumps({"username": "admin", "password": "i1c3-e2e-admin"}).encode(),
                   "application/json")
print(f"  HTTP={st2}  body={b2.decode('utf-8','replace')[:150]}")

print("")
print("=== 3) JSON POST /api/auth/login（对照，此前实测 200）===")
st3, b3, h3 = post("/api/auth/login", _j.dumps({"username": "admin", "password": "i1c3-e2e-admin"}).encode(),
                   "application/json")
print(f"  HTTP={st3}  body={b3.decode('utf-8','replace')[:150]}")
print(f"  Set-Cookie={h3.get('Set-Cookie','(无)')[:120]}")

print("")
print("=== 4) GET ${ADMIN}/login（确认路由存在）===")
try:
    with urllib.request.urlopen(API + f"{ADMIN}/login", timeout=10) as r:
        print(f"  HTTP={r.status}  len={len(r.read())}")
except Exception as e:
    print(f"  ERR {e}")

print("")
print("=== 5) 管理台登录页的表单 action（前端契约）===")
import io
P = USDT_ROOT + r"\03-web-admin\static\admin_login.html"
if os.path.isfile(P):
    s = io.open(P, encoding="utf-8", errors="replace").read()
    import re
    for m in re.finditer(r"<form[^>]*>", s):
        print("  ", m.group(0)[:180])
    for m in re.finditer(r'name=["\'](username|password)["\']', s):
        print("  input name:", m.group(1))
