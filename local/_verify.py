# -*- coding: utf-8 -*-
"""核心闭环综合验证：Go / Node / 落地页 / 管理台 四条链路。"""
import base64, json, time, urllib.request, urllib.error, subprocess

GO = "http://127.0.0.1:8888"
NODE = "http://127.0.0.1:3313"
LP = "http://127.0.0.1:8080"
ADMIN = "http://127.0.0.1:8898"


def req(url, method="GET", data=None, token=None):
    h = {"Content-Type": "application/json"}
    if token:
        h["x-token"] = token
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=15) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, {"_raw": e.read()[:120].decode("utf-8", "ignore")}
    except Exception as e:
        return 0, {"_err": str(e)}


def go_login():
    import ddddocr
    ocr = ddddocr.DdddOcr(show_ad=False)
    for attempt in range(5):
        _, cap = req(GO + "/base/captcha", "POST", {})
        if "data" not in cap:
            time.sleep(2); continue
        code = ocr.classification(base64.b64decode(cap["data"]["picPath"].split(",", 1)[1]))
        _, r = req(GO + "/base/login", "POST",
                   {"username": "admin", "password": "123456", "captcha": code, "captchaId": cap["data"]["captchaId"]})
        if r.get("code") == 0:
            return r["data"]["token"], attempt + 1
        time.sleep(1)
    return None, 5


tok, tries = go_login()
print(f"[Go] 登录成功 (尝试{tries}次) token={tok[:20]}...")

print("--- Go 业务 API ---")
for n, p, m, d in [("设备列表", "/device/list", "POST", {"page": 1, "pageSize": 5}),
                   ("钱包列表", "/device/wallet_list", "POST", {"page": 1, "pageSize": 5}),
                   ("分包列表", "/device/packet_list", "GET", None),
                   ("首页统计", "/device/get_index_info", "GET", None),
                   ("用户信息", "/user/getUserInfo", "GET", None)]:
    _, r = req(GO + p, m, d, tok)
    print(f"  {n:8s} {p:26s} code={r.get('code')}")

print("--- Node 后端 (3313) ---")
for n, p, m, d in [("Pixel配置", "/api/pixel-config", "GET", None),
                   ("落地设置", "/api/settings", "GET", None),
                   ("埋点start", "/api/track/start", "POST", {"sid": "verify1", "url": "http://localhost"}),
                   ("重放埋点", "/api/track", "POST", {"sid": "verify1", "type": "click"})]:
    st, r = req(NODE + p, m, d)
    print(f"  {n:8s} {p:22s} HTTP {st} {str(r)[:45]}")
out = subprocess.run(["docker", "exec", "iusdt-mongo", "mongosh", "--quiet", "--eval",
                      "db.getSiblingDB('gasleak').getCollectionNames().length"], capture_output=True, text=True)
print(f"  Mongo gasleak 集合数 = {out.stdout.strip() or out.stderr.strip()[:60]}")

print("--- 落地页 (8080, /api 反代到 Node) ---")
for n, p, m, d in [("模板", "/landing-pages/bokepx/", "GET", None),
                   ("runtime", "/landing-runtime.js", "GET", None),
                   ("埋点start", "/api/track/start", "POST", {"sid": "v2", "url": "x"})]:
    st, r = req(LP + p, m, d)
    print(f"  {n:8s} {p:26s} HTTP {st} {str(r)[:40]}")

print("--- 管理台 (8898) ---")
try:
    with urllib.request.urlopen(ADMIN + "/", timeout=10) as r3:
        html = r3.read().decode("utf-8", "ignore")
    print(f"  首页 HTTP {r3.status}, 页面字符数={len(html)}")
except Exception as e:
    print(f"  首页 ERROR {e}")
print("[OK] 验证结束")
