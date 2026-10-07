# -*- coding: utf-8 -*-
"""探测：无 token + 正确 multipart 时，鉴权与 multipart 解析的优先级。"""
import urllib.request
import urllib.error
import uuid

b = "----chk" + uuid.uuid4().hex
parts = []
parts.append(f"--{b}\r\n".encode())
parts.append(b'Content-Disposition: form-data; name="apk"; filename="t.apk"\r\n')
parts.append(b"Content-Type: application/octet-stream\r\n\r\n")
parts.append(b"PK\x03\x04test")
parts.append(f"\r\n--{b}--\r\n".encode())
body = b"".join(parts)

url = "http://127.0.0.1:3000/mgr-admin-8bcde2021d98/api/apk/upload"
req = urllib.request.Request(url, data=body, method="POST")
req.add_header("Content-Type", f"multipart/form-data; boundary={b}")

try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print(f"  无 token + 正确 multipart => HTTP {r.status}  body={r.read()[:150]}")
except urllib.error.HTTPError as e:
    print(f"  无 token + 正确 multipart => HTTP {e.code}  body={e.read()[:150]}")
except Exception as e:
    print(f"  ERR {e}")
