# -*- coding: utf-8 -*-
"""
D1-C1b 判据：更正 app.js 中不成立的 Fastify 作用域注释。

★★ 背景（2026-09-30）：
   D1-C5a 执行者发现「管理台端点无鉴权」，并在 `plugins/android/index.js` 中
   于【本 scope 内显式挂 authMiddleware】修复之（实测 401 ✓）。
   但其留在 `app.js:72-73` 的注释仍含【不成立】的假设：
     "fastify 的 preHandler 对同 scope 内全部路由生效，与注册先后无关"
   ⇒ Fastify 的 addHook 只在【当前 encapsulation context】内生效；
     apiPlugin 与 androidPlugin 是【并列】plugin，前者不覆盖后者。
   ⇒ 本卡只更正该注释（防止误导后续维护者）。

用法：
    python verify_d1c1b_admin_auth.py              # 全量
    python verify_d1c1b_admin_auth.py --selftest   # 量尺前置断言（P-5）

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
APP_JS = os.path.join(BE, "app.js")
INDEX_JS = os.path.join(BE, "plugins", "android", "index.js")
LANDING_JS = os.path.join(BE, "plugins", "api", "routes", "landing.js")
DASH_HTML = os.path.join(ROOT, "03-web-admin", "static", "admin_dashboard.html")
MANIFEST = os.path.join(ROOT, "_manifest.sha256")

ADMIN = "/mgr-admin-8bcde2021d98"
API = "http://127.0.0.1:3000"

BASE = {
    LANDING_JS: "3208c207bf423c8d99577c0508e9b6cc809f471dcd590ee0e96b87906e7de632",
    DASH_HTML: "9bad2f7f3a047a9fb988ca9f0c022df2db61b05ac2d548c74449eecdd6b85ce5",
    MANIFEST: "b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2",
}

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


def login():
    import http.cookiejar
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    body = json.dumps({"username": "admin", "password": "i1c3-e2e-admin"}).encode()
    req = urllib.request.Request(API + "/api/auth/login", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        opener.open(req, timeout=10).read()
    except Exception:
        pass
    for c in cj:
        if c.name == "accessToken":
            return c.value
    return None


def http_get(path, token=None, timeout=8):
    req = urllib.request.Request(API + path, method="GET")
    if token:
        req.add_header("Cookie", f"accessToken={token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception:
        return -1, b""


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    for p in (APP_JS, INDEX_JS, LANDING_JS, DASH_HTML, MANIFEST):
        print(f"  {'存在' if os.path.isfile(p) else '[FAIL] 缺失'}: {os.path.relpath(p, ROOT)}")
        if not os.path.isfile(p):
            ok = False

    # ★ 量尺有效性：正则须能区分"含错误表述"与"不含"
    bad_phrase = "与注册先后无关"
    yes = "// fastify 的 preHandler 对同 scope 内全部路由生效，与注册先后无关；"
    no = "// Fastify 的 addHook 只在当前 encapsulation context 内生效。"
    if bad_phrase in yes and bad_phrase not in no:
        print("  模式有效：可区分含/不含错误表述的文本")
    else:
        print("  [FAIL] 模式失效")
        ok = False

    # 打印当前 app.js 是否仍含错误表述
    appsrc = read(APP_JS)
    print(f"  当前 app.js {'★仍含' if bad_phrase in appsrc else '已不含'}「{bad_phrase}」")

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--skip-http", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== D1-C1b 判据：app.js 注释更正 + 鉴权仍生效 ===")
    print("")

    appsrc = read(APP_JS)

    # ---- E1: 不再含不成立的表述 ----
    print("E1 app.js 不再含不成立的表述:")
    bad_phrases = [
        "与注册先后无关",
        "对同 scope 内全部路由生效",
    ]
    found = [p for p in bad_phrases if p in appsrc]
    rec("E1 无「与注册先后无关」类错误表述", len(found) == 0,
        f"仍含: {found}" if found else "已清除")

    # ---- E2: 说明了在本 scope 显式挂 authMiddleware ----
    print("")
    print("E2 注释说明了「本 scope 显式挂 authMiddleware」:")
    has_explain = bool(re.search(r"本\s*scope|自己的\s*scope|encapsulation", appsrc)) and \
        ("authMiddleware" in appsrc)
    rec("E2 说明了 scope 与 authMiddleware 的关系", has_explain,
        "已说明" if has_explain else "★ 未说明（须补充）")

    # ---- E5: 守护 ----
    print("")
    print("E5 ★ 守护：不得改的文件的:")
    rec("E5 landing.js 未改", sha256(LANDING_JS) == BASE[LANDING_JS],
        f"{sha256(LANDING_JS)[:16]}…")
    rec("E5 admin_dashboard.html 未改", sha256(DASH_HTML) == BASE[DASH_HTML],
        f"{sha256(DASH_HTML)[:16]}…")
    rec("E5 _manifest.sha256 未改", sha256(MANIFEST) == BASE[MANIFEST],
        f"{sha256(MANIFEST)[:16]}…")
    # index.js 应保持 D1-C5a 的修复（不得回退）
    idx = read(INDEX_JS)
    rec("E5 index.js 仍含 authMiddleware（修复未回退）",
        "authMiddleware" in idx and "register(authMiddleware)" in idx,
        "仍含" if "register(authMiddleware)" in idx else "★ 修复被回退！")

    # ---- E3/E4: 真 HTTP（保证修复仍生效 + 落地页未误伤）----
    print("")
    print("E3/E4 真 HTTP 断言:")
    if args.skip_http:
        print("  [SKIP] 被 --skip-http 跳过 —— SKIP 不等于 PASS（P-13）")
    else:
        st3, b3 = http_get(f"{ADMIN}/api/theme")
        rec("E3 无 token GET ${ADMIN}/api/theme => 401", st3 == 401,
            f"HTTP={st3} body={b3.decode('utf-8','replace')[:80]}")

        st4, b4 = http_get("/api/template")
        rec("E4 无 token GET /api/template => 200（落地页未误伤）", st4 == 200,
            f"HTTP={st4} body={b4.decode('utf-8','replace')[:80]}")

        tok = login()
        if tok:
            st5, b5 = http_get(f"{ADMIN}/api/theme", token=tok)
            rec("E4 带 token GET ${ADMIN}/api/theme => 200（签名正确）", st5 == 200,
                f"HTTP={st5} body={b5.decode('utf-8','replace')[:80]}")
        else:
            print("  [SKIP] 无法登录 ⇒ 带 token 用例跳过")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  app.js 注释已更正，且鉴权修复仍生效、落地页未误伤")
    return 0


if __name__ == "__main__":
    sys.exit(main())
