# -*- coding: utf-8 -*-
"""端到端验证：Go 后端登录(OCR 过验证码) + 业务 API 调用。"""
import base64, json, sys, urllib.request

GO = "http://127.0.0.1:8888"

def post(path, data, token=None):
    req = urllib.request.Request(GO + path, data=json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    if token: req.add_header("x-token", token)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def get(path, token=None):
    req = urllib.request.Request(GO + path, method="GET")
    if token: req.add_header("x-token", token)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

# 1. 拿验证码
cap = post("/base/captcha", {})
cid = cap["data"]["captchaId"]
b64 = cap["data"]["picPath"].split(",", 1)[1]
img = base64.b64decode(b64)

import ddddocr
code = ddddocr.DdddOcr(show_ad=False).classification(img)
print(f"[1] 验证码 captchaId={cid} OCR识别={code}")

# 2. 登录
r = post("/base/login", {"username": "admin", "password": "123456", "captcha": code, "captchaId": cid})
print(f"[2] 登录 code={r.get('code')} msg={r.get('msg')}")
if r.get("code") != 0:
    # 重试一次（OCR 可能错）
    cap = post("/base/captcha", {})
    cid = cap["data"]["captchaId"]
    code = ddddocr.DdddOcr(show_ad=False).classification(base64.b64decode(cap["data"]["picPath"].split(",",1)[1]))
    r = post("/base/login", {"username": "admin", "password": "123456", "captcha": code, "captchaId": cid})
    print(f"[2b] 重试 code={r.get('code')} msg={r.get('msg')}")

if r.get("code") != 0:
    print("登录失败，退出"); sys.exit(1)
token = r["data"]["token"]
print(f"[3] token 前 24 位: {token[:24]}...")

# 3. 业务 API
for name, path, method in [
    ("getUserInfo", "/user/getUserInfo", "GET"),
    ("getServerInfo", "/system/getServerInfo", "GET"),
    ("device_list", "/device/device_list", "POST"),
    ("packet_list", "/device/packet_list", "GET"),
    ("get_index_info", "/device/get_index_info", "GET"),
]:
    try:
        resp = get(path, token) if method == "GET" else post(path, {"page":1,"pageSize":10}, token)
        print(f"[4] {name:16s} code={resp.get('code')} msg={str(resp.get('msg'))[:40]}")
    except Exception as e:
        print(f"[4] {name:16s} ERROR {e}")
print("[OK] Go 后端端到端验证完成")
