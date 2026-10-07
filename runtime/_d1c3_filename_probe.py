# -*- coding: utf-8 -*-
"""诊断：@fastify/multipart 交付的 part.filename 到底是什么？"""
import http.cookiejar
import json
import urllib.request
import uuid

API = "http://127.0.0.1:3000"
ADMIN = "/mgr-admin-8bcde2021d98"

# 用 raw 字节手工构造 multipart，精确控制 filename 值
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
b = json.dumps({"username": "admin", "password": "i1c3-e2e-admin"}).encode()
r = urllib.request.Request(API + "/api/auth/login", data=b, method="POST")
r.add_header("Content-Type", "application/json")
with op.open(r, timeout=10) as x:
    x.read()
tok = None
for c in cj:
    if c.name == "accessToken":
        tok = c.value

for fn in ["../../evilA.apk", "..\\..\\evilB.apk", "sub/evilC.apk", "plain.apk"]:
    bnd = "----DSH" + uuid.uuid4().hex
    data = b"".join([
        ("--%s\r\n" % bnd).encode(),
        ('Content-Disposition: form-data; name="apk"; filename="%s"\r\n' % fn).encode(),
        b"Content-Type: application/octet-stream\r\n\r\n",
        b"PK\x03\x04X",
        ("\r\n--%s--\r\n" % bnd).encode(),
    ])
    req = urllib.request.Request(API + ADMIN + "/api/apk/upload", data=data, method="POST")
    req.add_header("Content-Type", "multipart/form-data; boundary=" + bnd)
    req.add_header("Cookie", "accessToken=" + tok)
    try:
        with urllib.request.urlopen(req, timeout=30) as rr:
            print("sent=%-20r -> HTTP=%s %s" % (fn, rr.status, rr.read().decode("utf-8", "replace")))
    except urllib.error.HTTPError as e:
        print("sent=%-20r -> HTTP=%s %s" % (fn, e.code, e.read().decode("utf-8", "replace")))
    except Exception as e:
        print("sent=%-20r -> EXC=%s" % (fn, e))
