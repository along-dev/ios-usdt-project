# -*- coding: utf-8 -*-
"""
X6b 判据：${ADMIN}/dashboard 路由缺失（登录成功后 404）。

★★ 缺陷（X6 判据实测 + Node 日志确证）：
   · POST ${ADMIN}/login（正确凭据）⇒ 302，Location = ${ADMIN}/dashboard
   · GET  ${ADMIN}/dashboard ⇒ **404**（UNMATCHED）
   · 且**无人提供** admin_dashboard.html（60,126 B）⇒ 整个管理台 UI 不可达

★ 本卡：新增 GET ${ADMIN}/dashboard 路由，返回 admin_dashboard.html。

用法：
    python verify_x6b_dashboard.py              # 全量
    python verify_x6b_dashboard.py --selftest   # 量尺前置断言（P-5）

退出码：0 = 全绿；非 0 = 有红。
"""
from __future__ import annotations

import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

# ★ X3：自带 UTF-8 输出
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = USDT_ROOT
ADMIN_JS = os.path.join(ROOT, "02-backend-node", "src_restored", "plugins", "android", "admin.js")
DASH_HTML = os.path.join(ROOT, "03-web-admin", "static", "admin_dashboard.html")
MANIFEST = os.path.join(ROOT, "_manifest.sha256")

API = "http://127.0.0.1:3000"
ADMIN = "/mgr-admin-8bcde2021d98"
CREDS = {"username": "admin", "password": "i1c3-e2e-admin"}

BASE_ADMIN_JS = "c5df8ad45fcd786cf154d484448b3b4cc27c88b6d8954e7ba57682c019e6895a"
BASE_DASH = "9bad2f7f3a047a9fb988ca9f0c022df2db61b05ac2d548c74449eecdd6b85ce5"
MANIFEST_SHA = "b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2"

_results = []


def rec(name, ok, detail):
    _results.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def read(p):
    return open(p, encoding="utf-8", errors="replace").read()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def http(method, path, body=None, token=None, timeout=12, raw=None, ctype=None, follow=True,
         with_headers=False):
    data = None
    if raw is not None:
        data = raw
    elif body is not None:
        data = json.dumps(body).encode()
    req = urllib.request.Request(API + path, data=data, method=method)
    if ctype:
        req.add_header("Content-Type", ctype)
    elif data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Cookie", f"accessToken={token}")
    try:
        if follow:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return _ret(r.status, r.read(), dict(r.headers), r.headers, with_headers)
        op = urllib.request.build_opener(NoRedirect)
        with op.open(req, timeout=timeout) as r:
            return _ret(r.status, r.read(), dict(r.headers), r.headers, with_headers)
    except urllib.error.HTTPError as e:
        return _ret(e.code, e.read(), dict(e.headers or {}), e.headers, with_headers)
    except Exception as e:
        return _ret(-1, f"EXC:{e}".encode(), {}, None, with_headers)


def _ret(status, body, headers, raw_headers, with_headers):
    """★ X6b 量尺修复：dict(headers) 会【折叠重名响应头】——
    `Set-Cookie` 有 accessToken + refreshToken 两条，转 dict 后只剩一条、
    且键名大小写不定，导致 login_token() 永远取不到 token
    （Y2/Y3/Y6 被 SKIP、Y4 裸发无 cookie ⇒ 假红）。
    故额外回传原始 HTTPMessage，供 get_all('Set-Cookie') 取全部 cookie。
    """
    if with_headers:
        return status, body, headers, raw_headers
    return status, body, headers


def cookies_of(headers_msg):
    """从原始 HTTPMessage 取全部 Set-Cookie（含 accessToken）。"""
    if headers_msg is None:
        return []
    try:
        return headers_msg.get_all("Set-Cookie") or []
    except Exception:
        return []


def cookie_header_from(headers_msg):
    """把全部 Set-Cookie 的首段拼成请求用 Cookie 头。"""
    out = []
    for c in cookies_of(headers_msg):
        kv = str(c).split(";", 1)[0].strip()
        if kv:
            out.append(kv)
    return "; ".join(out)


def set_cookie_joined(headers_msg):
    """等价于「单条 Set-Cookie」，但保留全部 cookie 的键值，供正则提取。"""
    return ", ".join(cookies_of(headers_msg))


def login_token():
    st, b, h, raw_h = http("POST", "/api/auth/login", body=CREDS, with_headers=True)
    body = b.decode("utf-8", "replace")
    m = re.search(r'"accessToken"\s*:\s*"([^"]+)"', body)
    if m:
        return m.group(1)
    # ★ 修复：优先从原始 HTTPMessage 取全部 Set-Cookie（dict 会丢重名头）
    m2 = re.search(r"accessToken=([^;]+)", set_cookie_joined(raw_h))
    if m2:
        return m2.group(1)
    sc = str(h.get("Set-Cookie", ""))
    m2 = re.search(r"accessToken=([^;]+)", sc)
    return m2.group(1) if m2 else None


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    for p in (ADMIN_JS, DASH_HTML):
        e = os.path.isfile(p)
        print(f"  {'存在' if e else '[FAIL] 缺失'}: {os.path.relpath(p, ROOT)}"
              + (f"（{os.path.getsize(p):,} B）" if e else ""))
        if not e:
            ok = False
    st, _b, _h = http("GET", "/healthz")
    print(f"  Node :3000/healthz => HTTP={st}")
    if st != 200:
        print("  [FAIL] 服务未就绪")
        ok = False
    # ★ 量尺有效性：路由当前应【不存在】（红态）
    st2, _b2, _h2 = http("GET", f"{ADMIN}/dashboard")
    print(f"  当前 GET {ADMIN}/dashboard => HTTP={st2}"
          + ("（红态：待实现）" if st2 == 404 else ""))
    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== X6b 判据：${ADMIN}/dashboard 路由 ===")
    print("★ 缺陷：登录成功 302 到 ${ADMIN}/dashboard，但该路由【不存在】⇒ 404")
    print("")

    tok = login_token()
    print(f"  （登录 token：{'已取到' if tok else '★ 未取到'}）")
    print("")

    # ---- Y1: 无 token ⇒ 401（若选受保护域） ----
    st1, b1, _h1 = http("GET", f"{ADMIN}/dashboard")
    rec("Y1 无 token GET ${ADMIN}/dashboard ⇒ 401（受保护）", st1 == 401,
        f"HTTP={st1}")

    # ---- Y2: 带 token ⇒ 200 + text/html ----
    if tok:
        st2, b2, h2 = http("GET", f"{ADMIN}/dashboard", token=tok)
        ct = ""
        for k, v in h2.items():
            if k.lower() == "content-type":
                ct = v
        is_html = "text/html" in ct
        rec("Y2 带 token ⇒ 200 且 Content-Type 为 text/html",
            st2 == 200 and is_html, f"HTTP={st2} ct={ct} len={len(b2)}")

        # ---- Y3: 响应体含关键特征 ----
        body = b2.decode("utf-8", "replace")
        has_admin = ADMIN in body
        has_doctype = body.lstrip().lower().startswith("<!doctype html>") or "<html" in body[:2000].lower()
        rec("Y3 响应体是 admin_dashboard.html（含 ADMIN 常量 + HTML 结构）",
            has_admin and has_doctype,
            f"含 ADMIN={has_admin} 含 HTML={has_doctype} 前60={body[:60]!r}")
    else:
        print("  [SKIP] Y2/Y3 未取到 token —— SKIP 不等于 PASS（P-13）")

    # ---- Y4: ★ 端到端（登录 → 302 → 跟随 → 200）----
    print("")
    print("Y4 ★ 端到端：登录 → 302 → 跟随 Location → 200:")
    form = urllib.parse.urlencode(CREDS).encode()
    st4, _b4, h4, raw4 = http("POST", f"{ADMIN}/login", raw=form,
                              ctype="application/x-www-form-urlencoded", follow=False,
                              with_headers=True)
    loc = ""
    for k, v in h4.items():
        if k.lower() == "location":
            loc = v
    # ★ 修复：302 响应下发 accessToken cookie（浏览器会带着它跟随 Location）。
    #   原判据裸发第二个 GET ⇒ 必然 401，与被测路由无关（假红）。
    jar = cookie_header_from(raw4)
    print(f"    POST /login ⇒ HTTP={st4}  Location={loc}")
    print(f"    302 下发 Cookie：{'有（accessToken 已带上跟随）' if 'accessToken=' in jar else '★ 无'}")
    if loc:
        target = loc if loc.startswith("/") else "/"
        # ★ 带 302 下发的 cookie 重新请求（等价浏览器跟随 302）
        mtok = re.search(r"accessToken=([^;]+)", jar)
        st4b, b4b, h4b = http("GET", target, follow=False,
                              token=(mtok.group(1) if mtok else None))
        body4 = b4b.decode("utf-8", "replace")
        ct4 = ""
        for k, v in h4b.items():
            if k.lower() == "content-type":
                ct4 = v
        print(f"    跟随 GET {loc} ⇒ HTTP={st4b}  CT={ct4}  len={len(b4b)}")
        print(f"    响应体前 200 字节：{body4[:200]!r}")
        rec("Y4 ★ 登录后跟随 302 能到达 UI（200 + text/html）",
            st4b == 200 and "text/html" in ct4,
            f"GET {loc} ⇒ HTTP={st4b} ct={ct4}"
            + ("" if st4b == 200 else "  ★ 未达 200"))
    else:
        rec("Y4 登录返回 Location", False, "★ 无 Location")

    # ---- Y5: admin_dashboard.html 本体未改 ----
    print("")
    if os.path.isfile(DASH_HTML):
        cur = sha256(DASH_HTML)
        rec("Y5 ★ admin_dashboard.html 本体未改（契约来源只读）",
            cur == BASE_DASH, f"{cur[:16]}…")

    # ---- Y6: 既有 16 条管理台端点不回归 ----
    print("")
    if tok:
        eps = ["api/template", "api/theme", "api/pixel", "api/download-mode",
               "api/apk-url", "api/stats", "api/visits", "api/apk/list"]
        bad = []
        for e in eps:
            st, _b, _h = http("GET", f"{ADMIN}/{e}", token=tok)
            if st != 200:
                bad.append((e, st))
        rec("Y6 既有管理台端点无回归（8 条抽样全 200）", len(bad) == 0,
            f"★ 失败: {bad}" if bad else "8/8 全 200 ✓")

    # ---- Y7: 守护 ----
    print("")
    if os.path.isfile(MANIFEST):
        rec("Y7 _manifest.sha256 未改", sha256(MANIFEST) == MANIFEST_SHA,
            f"{sha256(MANIFEST)[:16]}…")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  登录后可真正到达管理台 UI（端到端打通）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
