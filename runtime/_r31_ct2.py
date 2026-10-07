# -*- coding: utf-8 -*-
"""定位 Content-Type 为空的原因：直接看 header 原始字节 + 试不同路径。"""
import socket
import urllib.request

PATHS = [
    "/images/template-previews/vodex.png",
    "/mgr-admin-8bcde2021d98/images/template-previews/vodex.png",
    "/mgr-admin-8bcde2021d98/dashboard",
    "/landing-pages/velocx/static/css/all.min.css",
    "/mgr-admin-8bcde2021d98/api/stats",
]

for p in PATHS:
    print("=== %s ===" % p)
    try:
        req = urllib.request.Request("http://127.0.0.1:3000" + p)
        with urllib.request.urlopen(req, timeout=8) as r:
            print("  status=%s" % r.status)
            for k, v in r.headers.items():
                print("    %-24s = %r" % (k, v))
    except Exception as e:
        print("  ERR %s %s" % (type(e).__name__, e))
    print("")

# ★ 用原始 socket 看未解析的响应头
print("=== 原始响应头（socket） ===")
try:
    s = socket.create_connection(("127.0.0.1", 3000), timeout=8)
    s.sendall(b"GET /images/template-previews/vodex.png HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
    buf = b""
    while b"\r\n\r\n" not in buf:
        c = s.recv(4096)
        if not c:
            break
        buf += c
    s.close()
    print(buf.decode("utf-8", "replace")[:700])
except Exception as e:
    print("  ERR", e)
