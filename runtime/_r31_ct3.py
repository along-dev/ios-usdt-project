# -*- coding: utf-8 -*-
"""确认 V2 失败是【判据脚本的 header 名大小写 bug】，而非服务缺陷。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import urllib.request

url = "http://127.0.0.1:3000/images/template-previews/vodex.png"

with urllib.request.urlopen(url, timeout=8) as r:
    h = dict(r.headers)
    b = r.read()

print("=== 各种取法 ===")
print("  r.headers.get('Content-Type')  =", repr(r.headers.get("Content-Type")))
print("  r.headers.get('content-type')  =", repr(r.headers.get("content-type")))
print("  r.headers.get('CONTENT-TYPE')  =", repr(r.headers.get("CONTENT-TYPE")))
print("  r.getheader('Content-Type')    =", repr(r.getheader("Content-Type")))
print("  r.getheader('content-type')    =", repr(r.getheader("content-type")))
print("")
print("  dict(r.headers) 的键 =", list(h.keys()))
print("  dict(r.headers).get('Content-Type') =", repr(h.get("Content-Type")))
print("  dict(r.headers).get('content-type') =", repr(h.get("content-type")))
print("")
print("=== 脚本 verify_t21_previews.py 的 http() 实现 ===")
import io
p = IOS_ROOT + r"\_integration\_fix_work\verify_t21_previews.py"
lines = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
for i in range(27, 48):
    if i < len(lines):
        print("  %4d: %s" % (i + 1, lines[i].rstrip()[:126]))
