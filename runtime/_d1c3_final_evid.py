# -*- coding: utf-8 -*-
"""D1-C3 最终证据：U3/U4/U5 真 HTTP 响应 + 落盘目录实测。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import http.cookiejar
import json
import os
import uuid
import urllib.error
import urllib.request

API = "http://127.0.0.1:3000"
ADMIN = "/mgr-admin-8bcde2021d98"
APK_DIR = USDT_ROOT + r"\02-backend-node\templates\apk"


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


def post(path, filename, content, token=None, field="apk"):
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
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, "EXC:" + str(e)


def ls(d):
    return sorted(os.listdir(d)) if os.path.isdir(d) else "MISSING"


tok = login()
U = ADMIN + "/api/apk/upload"
print("apk dir = %s" % APK_DIR)
print("")

print("---- U3 合法上传 ----")
print("BEFORE: %s" % ls(APK_DIR))
probe = "d1c3-final-%s.apk" % uuid.uuid4().hex[:8]
st, body = post(U, probe, b"PK\x03\x04" + b"D1C3FINAL" * 200, token=tok)
print("POST %s" % U)
print("  field=apk  filename=%s  HTTP=%s" % (probe, st))
print("  BODY=%s" % body)
print("AFTER : %s" % ls(APK_DIR))
fp = os.path.join(APK_DIR, probe)
print("  落盘实测: exists=%s bytes=%s" % (os.path.isfile(fp), os.path.getsize(fp) if os.path.isfile(fp) else "-"))

print("")
print("---- U4 路径穿越 filename=../../evil-d1c3.apk ----")
print("BEFORE parent  %s : %s" % (os.path.dirname(APK_DIR), ls(os.path.dirname(APK_DIR))))
print("BEFORE gp      %s : %s" % (os.path.dirname(os.path.dirname(APK_DIR)), ls(os.path.dirname(os.path.dirname(APK_DIR)))))
st4, body4 = post(U, "../../evil-d1c3.apk", b"PK\x03\x04EVIL", token=tok)
print("  HTTP=%s BODY=%s" % (st4, body4))
print("AFTER  parent  : %s" % ls(os.path.dirname(APK_DIR)))
print("AFTER  gp      : %s" % ls(os.path.dirname(os.path.dirname(APK_DIR))))
print("AFTER  apk dir : %s" % ls(APK_DIR))
for p in [os.path.join(os.path.dirname(APK_DIR), "evil-d1c3.apk"),
          os.path.join(os.path.dirname(os.path.dirname(APK_DIR)), "evil-d1c3.apk"),
          USDT_ROOT + r"\evil-d1c3.apk", r"E:\evil-d1c3.apk"]:
    print("  escape? %s -> %s" % (p, os.path.isfile(p)))

print("")
print("---- U5 非 .apk ----")
st5, body5 = post(U, "notanapk.txt", b"hello", token=tok)
print("  filename=notanapk.txt HTTP=%s BODY=%s" % (st5, body5))
print("  apk dir after: %s" % ls(APK_DIR))

print("")
print("---- U2 无 token ----")
st2, body2 = post(U, "nope.apk", b"PK\x03\x04x")
print("  HTTP=%s BODY=%s" % (st2, body2))

print("")
print("---- U6 大小上限（60MB）----")
st6, body6 = post(U, "huge.apk", b"PK\x03\x04" + b"\x00" * (60 * 1024 * 1024), token=tok)
print("  HTTP=%s BODY=%s" % (st6, body6))

print("")
print("---- U7 apk/list ----")
req = urllib.request.Request(API + ADMIN + "/api/apk/list", method="GET")
req.add_header("Cookie", "accessToken=" + tok)
with urllib.request.urlopen(req, timeout=10) as r:
    print("  HTTP=%s BODY=%s" % (r.status, r.read().decode("utf-8", "replace")[:400]))

print("")
print("---- 清理 ----")
for fn in os.listdir(APK_DIR) if os.path.isdir(APK_DIR) else []:
    if fn.startswith("d1c3-final-"):
        os.remove(os.path.join(APK_DIR, fn))
        print("  removed %s" % fn)
print("FINAL apk dir: %s" % ls(APK_DIR))
