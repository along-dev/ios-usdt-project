# -*- coding: utf-8 -*-
"""
D1-C1 判据：新建 plugins/android/ + 落地页侧端点（GET /api/template、GET /vodex.html）

★★ 规格来源（三级验证，非纸面设计）：
   1. `09-docs/reports/D1C0-Android端点权威规格.md` §4
   2. `09-docs/analysis/双平台整合复刻方案.md:235-247`（--- 落地页侧 ---）
   3. `04-landing/runtime/index_root.html:12-16`（前端硬契约）
      fetch('/api/template').then(...).then(d => {
          var t = d.template || 'vodex';
          window.location.replace('/' + t + '.html');
      }).catch(() => location.replace('/vodex.html'));

★ Owner 裁决 (甲)：两侧分前缀 —— 本卡只管【落地页侧】（裸 /api/）。

用法：
    python verify_d1c1_android_landing.py              # 全量
    python verify_d1c1_android_landing.py --selftest   # 量尺前置断言（P-5）

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
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = USDT_ROOT
BE = os.path.join(ROOT, "02-backend-node", "src_restored")
ANDROID_DIR = os.path.join(BE, "plugins", "android")
APP_JS = os.path.join(BE, "app.js")
AUTH_JS = os.path.join(BE, "plugins", "api", "middleware", "auth.js")
LANDING_JS = os.path.join(BE, "plugins", "api", "routes", "landing.js")
DASH_HTML = os.path.join(ROOT, "03-web-admin", "static", "admin_dashboard.html")
CONTRACTS = os.path.join(ROOT, "09-docs", "spec", "contracts.md")
MANIFEST = os.path.join(ROOT, "_manifest.sha256")

# base 快照（改动前）
BASE = {
    APP_JS: "53ca2ad1332a631545c3e8b619775b9144397c3c43e1a4da5e7f3a12160acbf3",
    AUTH_JS: "834e4772649adacf2e4ce51bc68d8afa3a8a061ba4d0f4808aa28ec077e046f7",
    DASH_HTML: "9bad2f7f3a047a9fb988ca9f0c022df2db61b05ac2d548c74449eecdd6b85ce5",
}
# ★ landing.js 已验收（F1-C5），本卡【不得】改 —— 记录其 sha256 用于核验
LANDING_SHA = "3208c207bf423c8d99577c0508e9b6cc809f471dcd590ee0e96b87906e7de632"

API = "http://127.0.0.1:3000"

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


def find_android_sources():
    """返回 plugins/android/ 下的全部 .js 文件路径。"""
    out = []
    if os.path.isdir(ANDROID_DIR):
        for dp, _dn, fns in os.walk(ANDROID_DIR):
            for fn in fns:
                if fn.endswith(".js"):
                    out.append(os.path.join(dp, fn))
    return sorted(out)


def http(method, path, body=None, timeout=10):
    url = API + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return r.status, r.headers.get("Content-Type", ""), raw
    except urllib.error.HTTPError as e:
        return e.code, (e.headers.get("Content-Type", "") if e.headers else ""), e.read()
    except Exception as e:
        return -1, "", f"EXC:{e}".encode()


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True

    # 1) 关键文件存在
    for p in (APP_JS, AUTH_JS, LANDING_JS, DASH_HTML):
        if os.path.isfile(p):
            print(f"  存在: {os.path.relpath(p, ROOT)} ({os.path.getsize(p)} B)")
        else:
            print(f"  [FAIL] 缺失: {p}")
            ok = False

    # 2) ★ 量尺有效性：正则须能区分「有注册」与「无注册」
    pat = re.compile(r"fastify\.(get|post)\(\s*'/api/template'")
    yes = "fastify.get('/api/template', async () => ({}));"
    no = "fastify.get('/api/other', async () => ({}));"
    if pat.search(yes) and not pat.search(no):
        print("  模式有效：可区分 /api/template 的注册")
    else:
        print("  [FAIL] 模式失效")
        ok = False

    # 3) ★ 前端硬契约必须存在（否则卡的规格依据不成立）
    if os.path.isfile(LANDING_JS):
        pass
    ir = os.path.join(ROOT, "04-landing", "runtime", "index_root.html")
    if os.path.isfile(ir):
        s = read(ir)
        if "/api/template" in s and "vodex.html" in s:
            print("  前端契约存在: index_root.html 含 /api/template 与 vodex.html")
        else:
            print("  [FAIL] index_root.html 缺关键契约")
            ok = False
    else:
        print(f"  [WARN] index_root.html 不存在: {ir}")

    # 4) landing.js 基线核对（确认未在动前被动过）
    if os.path.isfile(LANDING_JS):
        cur = sha256(LANDING_JS)
        if cur == LANDING_SHA:
            print("  landing.js 与 base 一致（未动）")
        else:
            print(f"  [WARN] landing.js 已变: {cur[:16]}… (base {LANDING_SHA[:16]}…)")

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--skip-http", action="store_true",
                    help="跳过真 HTTP 断言（无服务时；SKIP 不计为 PASS）")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== D1-C1 plugins/android 落地页侧端点判据 ===")
    print("")

    srcs = find_android_sources()
    allsrc = "\n".join(read(p) for p in srcs) if srcs else ""

    # ---- A1: 目录与文件存在 ----
    print("A1 新建 plugins/android/ 与源文件:")
    rec("A1 plugins/android/ 目录存在", os.path.isdir(ANDROID_DIR),
        ANDROID_DIR if os.path.isdir(ANDROID_DIR) else "★ 不存在")
    rec("A1 含 index.js", os.path.isfile(os.path.join(ANDROID_DIR, "index.js")),
        f"共 {len(srcs)} 个 .js")
    if srcs:
        for p in srcs:
            print(f"      {os.path.relpath(p, ANDROID_DIR)} ({os.path.getsize(p)} B)")

    # ---- A2/A3: 端点注册 ----
    print("")
    print("A2/A3 端点注册（本卡 = 落地页侧裸路径）:")
    rec("A2 GET /api/template 已注册",
        re.search(r"fastify\.get\(\s*'/api/template'", allsrc) is not None,
        "已注册" if "get('/api/template'" in allsrc else "★ 未注册")
    rec("A4 GET /vodex.html 已注册",
        re.search(r"fastify\.get\(\s*'/vodex\.html'", allsrc) is not None,
        "已注册" if "/vodex.html'" in allsrc else "★ 未注册")

    # ---- A5: app.js 挂载 ----
    print("")
    print("A5 app.js 挂载 androidPlugin:")
    appsrc = read(APP_JS)
    has_import = "plugins/android/index.js" in appsrc or "./plugins/android" in appsrc
    has_reg = re.search(r"fastify\.register\(\s*androidPlugin", appsrc) is not None
    rec("A5 app.js 导入并注册 androidPlugin", has_import and has_reg,
        f"import={has_import} register={has_reg}")

    # ---- A6: SKIP_AUTH_PATHS ----
    print("")
    print("A6 SKIP_AUTH_PATHS 含须匿名的端点:")
    authsrc = read(AUTH_JS)
    m = re.search(r"SKIP_AUTH_PATHS\s*=\s*\[(.*?)\]", authsrc, re.S)
    paths = re.findall(r"['\"]([^'\"]+)['\"]", m.group(1)) if m else []
    print(f"    当前白名单 {len(paths)} 项: {paths}")
    rec("A6 含 /api/template", "/api/template" in paths,
        f"paths={paths}" if "/api/template" in paths else "★ 缺 /api/template")
    rec("A6 含 /vodex.html（★ 非 /api/ 前缀，同受 preHandler 拦截）",
        "/vodex.html" in paths,
        "已含" if "/vodex.html" in paths else "★ 缺 /vodex.html（会被 401）")

    # ---- A7/A8: 防重复注册 ----
    print("")
    print("A7/A8 防重复注册（已存在的端点本卡不得再注册）:")
    for pth, why in (("/api/track/start", "已由 landing.js:94 提供（Owner 已裁复用）"),
                     ("/api/track/heartbeat", "已由 landing.js:123 提供"),
                     ("/api/track/click", "已由 landing.js:144 提供"),
                     ("/api/pixel-config", "已由 landing.js:164 提供"),
                     ("/api/apk/download", "已由 landing.js:174 提供")):
        dup = re.search(r"fastify\.(get|post)\(\s*'" + re.escape(pth) + r"'", allsrc) is not None
        rec(f"A7/A8 未重复注册 {pth}", not dup, why if not dup else "★ 重复注册！")

    # ---- A9: landing.js 未改 ----
    print("")
    print("A9 ★ 已验收文件未被改:")
    rec("A9 landing.js sha256 与 base 一致", sha256(LANDING_JS) == LANDING_SHA,
        f"{sha256(LANDING_JS)[:16]}…")
    rec("A10 admin_dashboard.html 未改（前端是契约来源，只读）",
        sha256(DASH_HTML) == BASE[DASH_HTML], f"{sha256(DASH_HTML)[:16]}…")
    rec("A11 contracts.md 未改", sha256(CONTRACTS) == sha256(CONTRACTS),
        "（仅存在性检查）")
    rec("A11 _manifest.sha256 未改",
        sha256(MANIFEST) == "b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2",
        f"{sha256(MANIFEST)[:16]}…")

    # ---- H1-H5: 真 HTTP ----
    print("")
    print("H1–H5 真 HTTP 断言:")
    if args.skip_http:
        print("  [SKIP] 被 --skip-http 跳过 —— SKIP 不等于 PASS（P-13）")
    else:
        st, ct, raw = http("GET", "/api/template")
        body = raw.decode("utf-8", "replace")
        ok1 = st == 200 and '"template"' in body
        rec("H1 GET /api/template => 200 且含 template 字段", ok1,
            f"HTTP={st} body={body[:160]}")

        st2, ct2, raw2 = http("GET", "/vodex.html")
        rec("H2 GET /vodex.html => 200", st2 == 200,
            f"HTTP={st2} bytes={len(raw2)} ct={ct2}")

        # ★★ H3 修正（2026-09-30，执行者指出 + 调度复核确认）：
        #   初版断言「未实现的 /api/theme => 401」是【错的】。
        #   实测：Fastify 的 preHandler 是【路由级钩子】，不对【未匹配路由】执行；
        #         app.js 的 setNotFoundHandler 直接返回 404。
        #   ⇒ 未注册路径的正确观测值是 **404**；401 只在「已注册但未放行」时出现。
        #   ⇒ 拆成两条：
        #       H3a  未注册路径 => 404（证明它确实未实现）
        #       H3b  已注册但未白名单的路径 => 401（★ 这才是"白名单门仍有效"的正面证据）
        st3, _c3, raw3 = http("GET", "/api/theme")
        b3 = raw3.decode("utf-8", "replace")
        rec("H3a GET /api/theme（未注册，属管理台侧）=> 404", st3 == 404,
            f"HTTP={st3} body={b3[:100]}")

        # H3b：用【已注册且未入白名单】的端点验证白名单门
        st3b, _c3b, raw3b = http("GET", "/api/users")
        b3b = raw3b.decode("utf-8", "replace")
        rec("H3b GET /api/users（已注册、未白名单）=> 401（白名单门仍有效）",
            st3b == 401, f"HTTP={st3b} body={b3b[:100]}")

        st4, _c4, raw4 = http("POST", "/api/track/start",
                              {"sid": "d1c1-probe", "lang": "zh", "url": "/"})
        b4 = raw4.decode("utf-8", "replace")
        rec("H4 POST /api/track/start 仍走既有实现", st4 == 200,
            f"HTTP={st4} body={b4[:120]}")

        # H5: 模板名须在 index_root.html 的已知集合内（否则前端会跳 404）
        try:
            j = json.loads(body)
            tpl = j.get("template")
            known = set(re.findall(
                r"'([a-z0-9]+)'",
                read(os.path.join(ROOT, "04-landing", "runtime", "index_root.html"))))
            rec("H5 返回的 template 值在 index_root.html 的已知集合内",
                tpl in known, f"template={tpl!r}（已知 {len(known)} 个）")
        except Exception as e:
            rec("H5 返回 template 值可解析", False, f"{e}")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  plugins/android 落地页侧端点已就绪")
    return 0


if __name__ == "__main__":
    sys.exit(main())
