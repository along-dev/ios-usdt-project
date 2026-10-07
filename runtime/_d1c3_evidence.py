# -*- coding: utf-8 -*-
"""D1-C3 证据采集：U3/U4/U5 真 HTTP 响应 + 落盘目录实测 + U4 落盘去向。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import http.cookiejar
import json
import os
import re
import urllib.error
import urllib.request
import uuid

API = "http://127.0.0.1:3000"
ADMIN = "/mgr-admin-8bcde2021d98"
APK_DIR = USDT_ROOT + r"\02-backend-node\templates\apk"
PARENT = USDT_ROOT + r"\02-backend-node\templates"
GRANDPARENT = USDT_ROOT + r"\02-backend-node"


def login():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    body = json.dumps({"username": "admin", "password": "i1c3-e2e-admin"}).encode()
    req = urllib.request.Request(API + "/api/auth/login", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    with op.open(req, timeout=10) as r:
        r.read()
    for c in cj:
        if c.name == "accessToken":
            return c.value
    return None


def multipart(path, field, filename, content, token=None, timeout=60):
    b = "----DSHB" + uuid.uuid4().hex
    data = b"".join([
        ("--%s\r\n" % b).encode(),
        ('Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (field, filename)).encode(),
        b"Content-Type: application/vnd.android.package-archive\r\n\r\n",
        content,
        ("\r\n--%s--\r\n" % b).encode(),
    ])
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


def listing(d):
    if not os.path.isdir(d):
        return "MISSING"
    return sorted(os.listdir(d))


tok = login()
print("token acquired = %s" % bool(tok))
print("")

# ---------- U3 ----------
probe = "d1c3-evid-%s.apk" % uuid.uuid4().hex[:8]
print("=== U3 上传合法 .apk ===")
print("before listdir(%s) = %s" % (APK_DIR, listing(APK_DIR)))
st, body = multipart(ADMIN + "/api/apk/upload", "apk", probe, b"PK\x03\x04" + b"EVID" * 256, token=tok)
print("POST %s/api/apk/upload  field=apk  filename=%s" % (ADMIN, probe))
print("HTTP=%s" % st)
print("BODY=%s" % body)
print("after  listdir(%s) = %s" % (APK_DIR, listing(APK_DIR)))
landed = os.path.join(APK_DIR, probe)
print("landed exists=%s size=%s" % (os.path.isfile(landed), os.path.getsize(landed) if os.path.isfile(landed) else "-"))

# ---------- U7 ----------
print("")
print("=== U7 apk/list ===")
req = urllib.request.Request(API + ADMIN + "/api/apk/list", method="GET")
req.add_header("Cookie", "accessToken=" + tok)
with urllib.request.urlopen(req, timeout=10) as r:
    lj = r.read().decode("utf-8", "replace")
print("GET %s/api/apk/list HTTP=200" % ADMIN)
print("BODY=%s" % lj[:500])

# ---------- U4 ----------
print("")
print("=== U4 路径穿越 ../../evil-d1c3.apk ===")
print("before:")
print("  parent      %s -> %s" % (PARENT, listing(PARENT)))
print("  grandparent %s -> %s" % (GRANDPARENT, listing(GRANDPARENT)))
st4, body4 = multipart(ADMIN + "/api/apk/upload", "apk", "../../evil-d1c3.apk", b"PK\x03\x04EVIL", token=tok)
print("HTTP=%s" % st4)
print("BODY=%s" % body4)
print("after:")
print("  parent      %s -> %s" % (PARENT, listing(PARENT)))
print("  grandparent %s -> %s" % (GRANDPARENT, listing(GRANDPARENT)))
for d in (PARENT, GRANDPARENT, "E:\\USDT项目", "E:\\"):
    p = os.path.join(d, "evil-d1c3.apk")
    print("  escape check %s : %s" % (p, os.path.isfile(p)))
print("  apk dir after = %s" % listing(APK_DIR))

# ---------- U5 ----------
print("")
print("=== U5 非 .apk 后缀 ===")
st5, body5 = multipart(ADMIN + "/api/apk/upload", "apk", "notanapk.txt", b"hello", token=tok)
print("HTTP=%s BODY=%s" % (st5, body5))
print("  apk dir after = %s" % listing(APK_DIR))

# ---------- U2 ----------
print("")
print("=== U2 无 token ===")
st2, body2 = multipart(ADMIN + "/api/apk/upload", "apk", "nope.apk", b"PK\x03\x04x")
print("HTTP=%s BODY=%s" % (st2, body2))

# ---------- 其它边界 ----------
print("")
print("=== 附加边界：反斜杠 / 空字节 / 字段名错 ===")
for fn in ("..\\..\\evil2.apk", "sub/evil3.apk"):
    s, b = multipart(ADMIN + "/api/apk/upload", "apk", fn, b"PK\x03\x04X", token=tok)
    print("  filename=%-22r HTTP=%s BODY=%s" % (fn, s, b[:120]))
s, b = multipart(ADMIN + "/api/apk/upload", "file", "wrongfield.apk", b"PK\x03\x04X", token=tok)
print("  field=file (错字段名)  HTTP=%s BODY=%s" % (s, b[:160]))

# ---------- 清理 ----------
print("")
print("=== 清理本次探测 ===")
for fn in os.listdir(APK_DIR) if os.path.isdir(APK_DIR) else []:
    if fn.startswith("d1c3-evid-"):
        os.remove(os.path.join(APK_DIR, fn))
        print("  removed %s" % fn)
print("final apk dir = %s" % listing(APK_DIR))
