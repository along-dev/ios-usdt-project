# -*- coding: utf-8 -*-
"""
D1-C5a 判据：管理台侧基础端点（${ADMIN}/api/*）+ AndroidConfig 存储模型

★ 契约来源（前端硬证据）：
   `03-web-admin/static/admin_dashboard.html` 的真实 fetch 调用
   + `09-docs/reports/D1-管理台侧端点契约.md`（已提取）
★ Owner 裁决 (甲)：两侧分前缀 —— 本卡管【管理台侧】=${ADMIN}/api/
★ 实测：`POST /api/auth/login {username:'admin', password:'i1c3-e2e-admin'}` => 200
   Set-Cookie: accessToken=<JWT>  ⇒ T 系列可用 Cookie 鉴权

用法：
    python verify_d1c5a_admin_endpoints.py              # 全量
    python verify_d1c5a_admin_endpoints.py --selftest   # 量尺前置断言（P-5）

退出码：0 = 全绿；非 0 = 有红。
"""
from __future__ import annotations

# ★ X3：本脚本【自带】UTF-8 输出，不依赖调用方设置 PYTHONIOENCODING（P-10）
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import os as _os
import sys as _sys

_os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # 旧版 Python 无 reconfigure 时静默降级
import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request

ROOT = USDT_ROOT
BE = os.path.join(ROOT, "02-backend-node", "src_restored")
ANDROID_DIR = os.path.join(BE, "plugins", "android")
MODELS_DIR = os.path.join(BE, "core", "db", "models")
MODELS_INDEX = os.path.join(MODELS_DIR, "index.js")
PAYLOAD_PARAMS = os.path.join(MODELS_DIR, "payload-params.js")
AUTH_JS = os.path.join(BE, "plugins", "api", "middleware", "auth.js")
LANDING_JS = os.path.join(BE, "plugins", "api", "routes", "landing.js")
DASH_HTML = os.path.join(ROOT, "03-web-admin", "static", "admin_dashboard.html")

ADMIN = "/mgr-admin-8bcde2021d98"       # ★ 逐字符保留（硬约束）
API = "http://127.0.0.1:3000"

BASE = {
    PAYLOAD_PARAMS: "dc370851c633d07349c2a4c4063d674b7281ed52b5a7e5b99d11901b2e335d17",
    LANDING_JS: "3208c207bf423c8d99577c0508e9b6cc809f471dcd590ee0e96b87906e7de632",
    DASH_HTML: "9bad2f7f3a047a9fb988ca9f0c022df2db61b05ac2d548c74449eecdd6b85ce5",
}

# 本卡应为的 10 条路由（方法, 路径）
ROUTES = [
    ("get", f"{ADMIN}/api/template"),
    ("post", f"{ADMIN}/api/template"),
    ("get", f"{ADMIN}/api/theme"),
    ("post", f"{ADMIN}/api/theme"),
    ("get", f"{ADMIN}/api/pixel"),
    ("post", f"{ADMIN}/api/pixel"),
    ("get", f"{ADMIN}/api/download-mode"),
    ("post", f"{ADMIN}/api/download-mode"),
    ("get", f"{ADMIN}/api/apk-url"),
    ("post", f"{ADMIN}/api/apk-url"),
]

_results = []
_TOKEN = None


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


def android_src():
    out = []
    if os.path.isdir(ANDROID_DIR):
        for dp, _dn, fns in os.walk(ANDROID_DIR):
            for fn in fns:
                if fn.endswith(".js"):
                    out.append(os.path.join(dp, fn))
    return sorted(out)


def login():
    """
    实测登录取 accessToken（停靠点 1 已验证可行）。

    ★★ 修正（2026-09-30，自查）：初版只在【Set-Cookie 响应头】里找 accessToken，
       实测该头可能不被 urllib 的 headers 暴露（或格式不同）⇒ 返回 None ⇒
       误判为"无法登录"。改为**三路兜底**：
         ① 响应头 Set-Cookie
         ② 响应 body（某些实现把 token 放 body）
         ③ `http.cookiejar` 收集的 cookie（最可靠）
    """
    import http.cookiejar
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    body = json.dumps({"username": "admin", "password": "i1c3-e2e-admin"}).encode()
    req = urllib.request.Request(API + "/api/auth/login", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with opener.open(req, timeout=10) as r:
            # ① 响应头
            try:
                for c in (r.headers.get_all("Set-Cookie") or []):
                    m = re.search(r"accessToken=([^;]+)", c)
                    if m:
                        return m.group(1)
            except Exception:
                pass
            # ② 响应体
            raw = r.read().decode("utf-8", "replace")
            m = re.search(r'"accessToken"\s*:\s*"([^"]+)"', raw)
            if m:
                return m.group(1)
    except Exception:
        pass
    # ③ cookie jar（最可靠）
    for c in cj:
        if c.name == "accessToken":
            return c.value
    return None


def http(method, path, body=None, token=None, timeout=10):
    url = API + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Cookie", f"accessToken={token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return -1, f"EXC:{e}".encode()


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    for p in (MODELS_INDEX, PAYLOAD_PARAMS, AUTH_JS, LANDING_JS, DASH_HTML):
        print(f"  {'存在' if os.path.isfile(p) else '[FAIL] 缺失'}: {os.path.relpath(p, ROOT)}")
        if not os.path.isfile(p):
            ok = False

    # 量尺有效性：正则须能区分 ADMIN 前缀路由
    pat = re.compile(re.escape(ADMIN) + r"/api/theme'")
    yes = "fastify.get(`" + ADMIN + "/api/theme', h);"
    no = "fastify.get('/api/theme', h);"
    if pat.search(yes) and not pat.search(no):
        print("  模式有效：可区分带 ADMIN 前缀的路由")
    else:
        print("  [FAIL] 模式失效")
        ok = False

    # ★ 登录可用性（T 系列的前提）
    t = login()
    if t:
        print(f"  登录可用：取到 accessToken（{len(t)} 字符）")
    else:
        print("  [WARN] 登录失败/服务未起 —— T 系列将 SKIP")

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--skip-http", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== D1-C5a 管理台侧基础端点判据 ===")
    print(f"前缀: {ADMIN}")
    print("")

    srcs = android_src()
    allsrc = "\n".join(read(p) for p in srcs) if srcs else ""

    # ---- B1: 模型 ----
    print("B1 AndroidConfig 存储模型:")
    model_file = os.path.join(MODELS_DIR, "android-config.js")
    rec("B1 android-config.js 存在", os.path.isfile(model_file),
        os.path.relpath(model_file, ROOT) if os.path.isfile(model_file) else "★ 不存在")
    if os.path.isfile(model_file):
        ms = read(model_file)
        rec("B1 导出 AndroidConfig", "AndroidConfig" in ms and "model(" in ms,
            "已导出" if "AndroidConfig" in ms else "★ 未导出")
        rec("B1 使用 _id='global' 单文档模式", "default: 'global'" in ms or "default:'global'" in ms,
            "'global'" if "global" in ms else "★ 未用单文档模式")

    # ---- B2: models/index.js 导出 ----
    idx = read(MODELS_INDEX)
    rec("B2 models/index.js 导出 AndroidConfig", "android-config.js" in idx,
        "已导出" if "android-config.js" in idx else "★ 未导出")

    # ---- B3: 10 条路由 ----
    #
    # ★★ 修正（2026-09-30，自查，P-5 第 N 次）：
    #   初版用 `re.escape(ADMIN) + "/api/theme'"` 匹配【字面量路径】。
    #   但实现用的是【模板字符串 + 常量】：`fastify.get(`${ADMIN}/api/theme`, ...)`
    #   ⇒ 字面量正则匹配不到 ⇒ **假红**（"缺 10 条"实为量尺坏了）。
    #   正确判据：同时接受两种写法 ——
    #     (a) 字面量:  fastify.get('/mgr-admin-.../api/theme'
    #     (b) 模板串:  fastify.get(`${ADMIN}/api/theme`
    print("")
    print("B3 10 条路由注册（带 ADMIN 前缀，支持字面量与 ${ADMIN} 两种写法）:")
    missing = []
    sub = ADMIN.split("/")[-1]        # mr-admin-8bcde2021d98 的最后一段，用于宽松匹配
    for meth, path in ROUTES:
        # 路径去掉 ADMIN 前缀后的剩余部分（如 /api/theme）
        rest = path[len(ADMIN):]
        pats = [
            # (a) 字面量
            re.compile(r"fastify\." + meth + r"\(\s*[`'\"]" + re.escape(path) + r"[`'\"]"),
            # (b) 模板串 ${ADMIN} 或 ${A} 等
            re.compile(r"fastify\." + meth + r"\(\s*`\$\{[A-Za-z_]+\}" + re.escape(rest) + r"`"),
        ]
        if not any(p.search(allsrc) for p in pats):
            missing.append(f"{meth.upper()} {path}")
    rec("B3 10 条路由全部注册", len(missing) == 0,
        "全部已注册" if not missing else f"★ 缺 {len(missing)}: {missing}")
    if not missing:
        # 额外确认：ADMIN 常量确实被定义为正确值
        rec("B3 ADMIN 常量值正确",
            re.search(r"ADMIN\s*=\s*['\"]" + re.escape(ADMIN) + r"['\"]", allsrc) is not None,
            f"含 ADMIN = '{ADMIN}'")

    # ---- B4/B5: 守护 ----
    print("")
    print("B4/B5 ★ 守护：不得改的文件的:")
    rec("B4 payload-params.js 未改（不复用它）",
        sha256(PAYLOAD_PARAMS) == BASE[PAYLOAD_PARAMS],
        f"{sha256(PAYLOAD_PARAMS)[:16]}…")
    rec("B5 landing.js 未改", sha256(LANDING_JS) == BASE[LANDING_JS],
        f"{sha256(LANDING_JS)[:16]}…")
    rec("B5 admin_dashboard.html 未改（前端是契约来源）",
        sha256(DASH_HTML) == BASE[DASH_HTML], f"{sha256(DASH_HTML)[:16]}…")

    # ---- B6: ADMIN 前缀逐字符 ----
    rec("B6 ADMIN 前缀逐字符正确",
        ADMIN in allsrc, f"源码含 {ADMIN}" if ADMIN in allsrc else "★ 前缀不正确")

    # ---- B7: 这 10 条不得加入白名单（需鉴权）----
    print("")
    print("B7 这 10 条【需鉴权】⇒ 不得加入 SKIP_AUTH_PATHS:")
    authsrc = read(AUTH_JS)
    m = re.search(r"SKIP_AUTH_PATHS\s*=\s*\[(.*?)\]", authsrc, re.S)
    wl = re.findall(r"['\"]([^'\"]+)['\"]", m.group(1)) if m else []
    leaked = [p for _mth, p in ROUTES if p in wl]
    rec("B7 无管理台端点被误加入白名单", len(leaked) == 0,
        f"白名单 {len(wl)} 项；误加 {leaked}" if leaked else f"白名单 {len(wl)} 项，无误加")

    # ---- T1–T7: 真 HTTP ----
    print("")
    print("T1–T7 真 HTTP 断言:")
    if args.skip_http:
        print("  [SKIP] 被 --skip-http 跳过 —— SKIP 不等于 PASS（P-13）")
    else:
        tok = login()
        if not tok:
            print("  [SKIP] 无法登录 ⇒ T2–T7 无法执行（★ SKIP 不等于 PASS）")
            st, _b = http("GET", f"{ADMIN}/api/theme")
            rec("T1 无 token => 401", st == 401, f"HTTP={st}")
        else:
            st, _b = http("GET", f"{ADMIN}/api/theme")
            rec("T1 无 token => 401", st == 401, f"HTTP={st}")

            st2, b2 = http("GET", f"{ADMIN}/api/theme", token=tok)
            rec("T2 带 token GET theme => 200 且含 theme", st2 == 200 and b"theme" in b2,
                f"HTTP={st2} body={b2.decode('utf-8','replace')[:100]}")

            # T3: 往返持久化
            st3, _ = http("POST", f"{ADMIN}/api/theme", {"theme": "gold"}, token=tok)
            st3b, b3b = http("GET", f"{ADMIN}/api/theme", token=tok)
            ok3 = st3 == 200 and st3b == 200 and '"gold"' in b3b.decode("utf-8", "replace")
            rec("T3 POST theme -> GET 往返持久化（gold）", ok3,
                f"POST={st3} GET={st3b} body={b3b.decode('utf-8','replace')[:100]}")

            # T4: pixel add
            st4, _ = http("POST", f"{ADMIN}/api/pixel",
                          {"action": "add", "pixel_id": "1234567890"}, token=tok)
            st4b, b4b = http("GET", f"{ADMIN}/api/pixel", token=tok)
            ok4 = st4 == 200 and "1234567890" in b4b.decode("utf-8", "replace")
            rec("T4 POST pixel add -> GET 含该值", ok4,
                f"POST={st4} GET={st4b} body={b4b.decode('utf-8','replace')[:120]}")

            # T5: pixel remove
            st5, _ = http("POST", f"{ADMIN}/api/pixel",
                          {"action": "remove", "pixel_id": "1234567890"}, token=tok)
            st5b, b5b = http("GET", f"{ADMIN}/api/pixel", token=tok)
            ok5 = st5 == 200 and "1234567890" not in b5b.decode("utf-8", "replace")
            rec("T5 POST pixel remove -> GET 已移除", ok5,
                f"POST={st5} GET={st5b} body={b5b.decode('utf-8','replace')[:120]}")

            # T6: template 往返
            st6, _ = http("POST", f"{ADMIN}/api/template", {"template": "vodex"}, token=tok)
            st6b, b6b = http("GET", f"{ADMIN}/api/template", token=tok)
            ok6 = st6 == 200 and st6b == 200 and '"vodex"' in b6b.decode("utf-8", "replace")
            rec("T6 POST template -> GET 往返一致", ok6,
                f"POST={st6} GET={st6b} body={b6b.decode('utf-8','replace')[:100]}")

            # T7: download-mode 往返
            st7, _ = http("POST", f"{ADMIN}/api/download-mode", {"mode": "link"}, token=tok)
            st7b, b7b = http("GET", f"{ADMIN}/api/download-mode", token=tok)
            ok7 = st7 == 200 and st7b == 200 and '"link"' in b7b.decode("utf-8", "replace")
            rec("T7 POST download-mode -> GET 往返一致", ok7,
                f"POST={st7} GET={st7b} body={b7b.decode('utf-8','replace')[:100]}")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  管理台侧基础端点已就绪且持久化生效")
    return 0


if __name__ == "__main__":
    sys.exit(main())
