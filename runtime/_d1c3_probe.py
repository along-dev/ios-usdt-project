# -*- coding: utf-8 -*-
"""D1-C3 现场探针：登录 / login 页 / upload 路由 / apk-list / index.js 结构影响。"""
import http.cookiejar
import json
import re
import urllib.error
import urllib.request
import uuid

API = "http://127.0.0.1:3000"
ADMIN = "/mgr-admin-8bcde2021d98"


def login():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    body = json.dumps({"username": "admin", "password": "i1c3-e2e-admin"}).encode()
    req = urllib.request.Request(API + "/api/auth/login", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with op.open(req, timeout=10) as r:
            raw = r.read().decode("utf-8", "replace")
        m = re.search(r'"accessToken"\s*:\s*"([^"]+)"', raw)
        return m.group(1) if m else "NOLOGIN:" + raw[:200]
    except urllib.error.HTTPError as e:
        return "HTTP%d:%s" % (e.code, e.read().decode("utf-8", "replace")[:200])
    except Exception as e:
        return "EXC:" + str(e)


def get(path, token=None, timeout=10):
    req = urllib.request.Request(API + path, method="GET")
    if token:
        req.add_header("Cookie", "accessToken=" + token)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, "EXC:" + str(e)


def multipart(path, field, filename, content, token=None, timeout=30):
    b = "----DSHB" + uuid.uuid4().hex
    parts = [("--%s\r\n" % b).encode(),
             ('Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (field, filename)).encode(),
             b"Content-Type: application/vnd.android.package-archive\r\n\r\n",
             content,
             ("\r\n--%s--\r\n" % b).encode()]
    data = b"".join(parts)
    req = urllib.request.Request(API + path, data=data, method="POST")
    req.add_header("Content-Type", "multipart/form-data; boundary=" + b)
    if token:
        req.add_header("Cookie", "accessToken=" + token)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, "EXC:" + str(e)


print("=== 1. GET ${ADMIN}/login (anonymous, must be 200 HTML) ===")
st, body = get(ADMIN + "/login")
print("HTTP=%s len=%s head=%r" % (st, len(body), body[:80]))

print("\n=== 2. POST /api/auth/login ===")
tok = login()
print("token=%s..." % tok[:28] if not tok.startswith(("NOLOGIN", "HTTP", "EXC")) else tok)

if not tok.startswith(("NOLOGIN", "HTTP", "EXC")):
    print("\n=== 3. GET ${ADMIN}/api/apk/list (with token) ===")
    st, body = get(ADMIN + "/api/apk/list", token=tok)
    print("HTTP=%s body=%s" % (st, body[:400]))

    print("\n=== 4. GET ${ADMIN}/api/apk/list (no token, expect 401) ===")
    st, body = get(ADMIN + "/api/apk/list")
    print("HTTP=%s body=%s" % (st, body[:200]))

print("\n=== 5. POST ${ADMIN}/api/apk/upload (expect 404 = not implemented) ===")
st, body = multipart(ADMIN + "/api/apk/upload", "apk", "probe.apk", b"PK\x03\x04probe")
print("no-token HTTP=%s body=%s" % (st, body[:200]))
if not tok.startswith(("NOLOGIN", "HTTP", "EXC")):
    st, body = multipart(ADMIN + "/api/apk/upload", "apk", "probe.apk", b"PK\x03\x04probe", token=tok)
    print("with-token HTTP=%s body=%s" % (st, body[:200]))
