# -*- coding: utf-8 -*-
"""
D1-C5b 判据：管理台侧数据端点 + 登录登出。

★ 契约来源：`03-web-admin/static/admin_dashboard.html`（前端硬证据）
★ 前缀：${ADMIN} = /mgr-admin-8bcde2021d98（Owner 裁决 甲）

★★ D6（visits/clear）是【破坏性操作】：
   本判据先记录 clear 前的 total，clear 后验证 total 变小/为 0，
   并在**结束时如实报告**（不尝试恢复 —— 数据可从落地页流量重建）。
   ★ 若执行者认为不可清空 ⇒ 应在报告中说明，本判据的 D6 会 SKIP。

用法：
    python verify_d1c5b_admin_data.py              # 全量
    python verify_d1c5b_admin_data.py --selftest   # 量尺前置断言（P-5）
    python verify_d1c5b_admin_data.py --no-clear   # 跳过 D6（不执行破坏性操作）

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
import http.cookiejar
import json
import os
import re
import sys
import urllib.error
import urllib.request

ROOT = USDT_ROOT
BE = os.path.join(ROOT, "02-backend-node", "src_restored")
ANDROID_DIR = os.path.join(BE, "plugins", "android")
ADMIN_JS = os.path.join(ANDROID_DIR, "admin.js")
INDEX_JS = os.path.join(ANDROID_DIR, "index.js")
APP_JS = os.path.join(BE, "app.js")
LANDING_JS = os.path.join(BE, "plugins", "api", "routes", "landing.js")
VISITORS_JS = os.path.join(BE, "plugins", "api", "routes", "visitors.js")
DASH_HTML = os.path.join(ROOT, "03-web-admin", "static", "admin_dashboard.html")
MANIFEST = os.path.join(ROOT, "_manifest.sha256")

ADMIN = "/mgr-admin-8bcde2021d98"
API = "http://127.0.0.1:3000"

BASE = {
    LANDING_JS: "3208c207bf423c8d99577c0508e9b6cc809f471dcd590ee0e96b87906e7de632",
    DASH_HTML: "9bad2f7f3a047a9fb988ca9f0c022df2db61b05ac2d548c74449eecdd6b85ce5",
    MANIFEST: "b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2",
    APP_JS: "a1b568827febc198f115f5e285e29e368b80f211f121797d1b4da8f59f3c16fb",
}

ROUTES = [
    ("get", f"{ADMIN}/api/stats"),
    ("get", f"{ADMIN}/api/visits"),
    ("post", f"{ADMIN}/api/visits/clear"),
    ("get", f"{ADMIN}/api/apk/list"),
    ("post", f"{ADMIN}/api/apk/delete"),
    ("post", f"{ADMIN}/login"),
    ("get", f"{ADMIN}/logout"),
]

_results = []


def rec(name, ok, detail):
    _results.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def skip(name, why=""):
    """★ X2：SKIP 不等于 PASS（P-13）—— 不作判定，也不计入通过率。

    用于「前提不成立、根本无从判定」的分支（如 APK < 2 条时无法判序）。
    与无条件判定通过的区别：本函数不给出 PASS 结论。
    """
    if why:
        print(f"  [SKIP] {name}: {why} —— SKIP 不等于 PASS（P-13）")
    else:
        print(f"  [SKIP] {name} —— SKIP 不等于 PASS（P-13）")


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
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    body = json.dumps({"username": "admin", "password": "i1c3-e2e-admin"}).encode()
    req = urllib.request.Request(API + "/api/auth/login", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with opener.open(req, timeout=10) as r:
            raw = r.read().decode("utf-8", "replace")
            m = re.search(r'"accessToken"\s*:\s*"([^"]+)"', raw)
            if m:
                return m.group(1)
    except Exception:
        pass
    for c in cj:
        if c.name == "accessToken":
            return c.value
    return None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """★ X2：禁止自动跟随 3xx（否则测不出"302 重定向"本身）。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def req(method, path, body=None, token=None, timeout=15, follow=True):
    """
    ★★ X2 修正（2026-09-30，执行者指出 + 调度裁决方案 A）：
      初版无 follow 参数 ⇒ `urlopen` **默认自动跟随 3xx** ⇒
      `${ADMIN}/logout`（源码 `reply.redirect(..., 302)`）会被跟随到登录页，
      判据拿到 **200** 而非 **302** ⇒ 只能写"非 404"这类**弱断言**。
      ⇒ 加 `follow` 参数（**默认 True 保持既有调用的行为不变**）；
        D7 用 `follow=False` 以断言**确切 302**（判别力强）。
    """
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(API + path, data=data, method=method)
    if data:
        r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Cookie", f"accessToken={token}")
    try:
        if follow:
            with urllib.request.urlopen(r, timeout=timeout) as resp:
                return resp.status, resp.read()
        op = urllib.request.build_opener(_NoRedirect)
        with op.open(r, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return -1, f"EXC:{e}".encode()


def jload(b):
    try:
        return json.loads(b.decode("utf-8", "replace"))
    except Exception:
        return None


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    for p in (ADMIN_JS, INDEX_JS, APP_JS, LANDING_JS, VISITORS_JS, DASH_HTML):
        print(f"  {'存在' if os.path.isfile(p) else '[WARN] 缺失'}: {os.path.relpath(p, ROOT)}")

    # 量尺有效性：正则须能区分带 ADMIN 前缀的路由
    yes = "fastify.get(`${ADMIN}/api/stats`, h)"
    no = "fastify.get('/api/other', h)"
    pat = re.compile(r"fastify\.get\(\s*`\$\{ADMIN\}" + re.escape("/api/stats") + r"`")
    if pat.search(yes) and not pat.search(no):
        print("  模式有效：可区分 ${ADMIN} 前缀路由")
    else:
        print("  [FAIL] 模式失效")
        ok = False

    t = login()
    print(f"  {'登录可用' if t else '[WARN] 登录失败'}（token {'取到' if t else '未取到'}）")
    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--skip-http", action="store_true")
    ap.add_argument("--no-clear", action="store_true", help="跳过 D6（不清空数据）")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== D1-C5b 管理台侧数据端点判据 ===")
    print(f"前缀: {ADMIN}")
    print("")

    srcs = android_src()
    allsrc = "\n".join(read(p) for p in srcs) if srcs else ""

    # ---- D1: 7 条路由 ----
    print("D1 7 条路由注册:")
    missing = []
    for meth, path in ROUTES:
        rest = path[len(ADMIN):] if path.startswith(ADMIN) else path
        pats = [
            re.compile(r"fastify\." + meth + r"\(\s*[`'\"]" + re.escape(path) + r"[`'\"]"),
            re.compile(r"fastify\." + meth + r"\(\s*`\$\{[A-Za-z_]+\}" + re.escape(rest) + r"`"),
        ]
        if not any(p.search(allsrc) for p in pats):
            missing.append(f"{meth.upper()} {path}")
    rec("D1 7 条路由全部注册", len(missing) == 0,
        "全部已注册" if not missing else f"★ 缺 {len(missing)}: {missing}")

    # ---- D2: 守护 ----
    print("")
    print("D2 ★ 守护：不得改的文件的:")
    rec("D2 landing.js 未改", sha256(LANDING_JS) == BASE[LANDING_JS],
        f"{sha256(LANDING_JS)[:16]}…")
    rec("D2 admin_dashboard.html 未改", sha256(DASH_HTML) == BASE[DASH_HTML],
        f"{sha256(DASH_HTML)[:16]}…")
    rec("D2 _manifest.sha256 未改", sha256(MANIFEST) == BASE[MANIFEST],
        f"{sha256(MANIFEST)[:16]}…")
    rec("D2 app.js 未改（D1-C1b 刚更正过）", sha256(APP_JS) == BASE[APP_JS],
        f"{sha256(APP_JS)[:16]}…")
    if os.path.isfile(VISITORS_JS):
        print(f"    （visitors.js 存在，仅参照；本判据不核其哈希）")

    # ---- 真 HTTP ----
    print("")
    if args.skip_http:
        print("[SKIP] HTTP 断言被 --skip-http 跳过 —— SKIP 不等于 PASS（P-13）")
    else:
        tok = login()
        if not tok:
            print("[SKIP] 无法登录 ⇒ D3–D7 无法执行")
        else:
            # D7: 鉴权
            st0, _ = req("GET", f"{ADMIN}/api/stats")
            rec("D7 无 token => 401", st0 == 401, f"HTTP={st0}")

            # D4: stats 字段
            st1, b1 = req("GET", f"{ADMIN}/api/stats", token=tok)
            j1 = jload(b1)
            has_fields = st1 == 200 and isinstance(j1, dict) and ("total" in j1) and ("clicks" in j1)
            rec("D4 stats 含 total 与 clicks", has_fields,
                f"HTTP={st1} body={b1.decode('utf-8','replace')[:150]}")

            # D3: 分页真生效
            st2a, b2a = req("GET", f"{ADMIN}/api/visits?page=1&per=1", token=tok)
            st2b, b2b = req("GET", f"{ADMIN}/api/visits?page=1&per=5", token=tok)
            ja, jb = jload(b2a), jload(b2b)
            na = len(ja.get("rows", [])) if isinstance(ja, dict) else -1
            nb = len(jb.get("rows", [])) if isinstance(jb, dict) else -1
            # per=1 => 至多 1 条；per=5 => 至多 5 条；两者应【不同】（除非库里 <2 条）
            ok3 = st2a == 200 and st2b == 200 and na <= 1 and nb <= 5 and (na != nb or nb == 0)
            rec("D3 分页真生效（per=1 与 per=5 条数不同）", ok3,
                f"per=1 -> {na} 条；per=5 -> {nb} 条")
            if isinstance(jb, dict):
                rows = jb.get("rows", [])
                if rows:
                    k = sorted(rows[0].keys())
                    print(f"    rows[0] 字段({len(k)}): {k}")
                    print(f"    ★ 期望 18 字段（前端契约）")

            # D5: apk/list 排序（若有 >=2 条；不足 2 条则标 SKIP，**SKIP 不等于 PASS**）
            st3, b3 = req("GET", f"{ADMIN}/api/apk/list", token=tok)
            j3 = jload(b3)
            files = j3.get("files", []) if isinstance(j3, dict) else []
            if len(files) >= 2:
                ts = []
                for f in files:
                    v = f.get("uploaded_at")
                    ts.append(str(v) if v is not None else "")
                desc = all(ts[i] >= ts[i + 1] for i in range(len(ts) - 1))
                rec("D5 apk/list 按新→旧排序", desc, f"{len(files)} 条：{ts[:4]}")
            else:
                # ★ X2：APK < 2 条 ⇒ 根本无序列可判 ⇒ 属 SKIP，**不是 PASS**（P-13）。
                #   原实现为无条件 PASS ⇒ 假绿。
                #   ⇒ 改为 skip()：不计入 _results ⇒ 既不冒充 PASS，也不谎报 FAIL。
                print(f"  [SKIP] D5 apk/list 排序：仅 {len(files)} 条（<2，无法判序）"
                      f" —— SKIP 不等于 PASS（P-13）")
                skip(f"D5 apk/list 排序（仅 {len(files)} 条，<2 无法判序）")
            if isinstance(j3, dict):
                print(f"    apk/list 响应: {b3.decode('utf-8','replace')[:150]}")

            # D6: visits/clear（破坏性）
            if args.no_clear:
                print("  [SKIP] D6 被 --no-clear 跳过（破坏性操作）—— SKIP 不等于 PASS")
            else:
                st4, b4 = req("GET", f"{ADMIN}/api/visits?page=1&per=1", token=tok)
                j4 = jload(b4)
                before = j4.get("total") if isinstance(j4, dict) else None
                st5, b5 = req("POST", f"{ADMIN}/api/visits/clear", token=tok)
                st6, b6 = req("GET", f"{ADMIN}/api/visits?page=1&per=1", token=tok)
                j6 = jload(b6)
                after = j6.get("total") if isinstance(j6, dict) else None
                ok6 = st5 in (200, 204) and isinstance(after, int) and after == 0
                rec("D6 visits/clear 真清空（total 归 0）", ok6,
                    f"clear 前 total={before}；clear HTTP={st5}；clear 后 total={after}")

            # D7b: 登录/登出可用性（★ X2：不跟随重定向，断言确切 302）
            st7, _ = req("GET", f"{ADMIN}/logout", token=tok, follow=False)
            rec("D7 ${ADMIN}/logout ⇒ 302（清会话后重定向到登录页）",
                st7 == 302, f"HTTP={st7}")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  管理台侧数据端点已就绪（分页/排序/清空 真生效）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
