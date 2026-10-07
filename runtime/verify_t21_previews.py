"""T21 · 判据 V1-V7 验证（动前红 / 动后绿）。

用法:
  python verify_t21_previews.py            # 全量（V1-V7，需 3000 在跑）
  python verify_t21_previews.py --offline  # 只跑 V1/V6/V7（不需要服务）

退出码: 0 = 全绿；1 = 有红。
"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import os
import re
import sys
import json
import hashlib
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")

ROOT = USDT_ROOT
ADMIN = "/mgr-admin-8bcde2021d98"
BASE = "http://127.0.0.1:3000"
PREV_DIR = os.path.join(ROOT, "03-web-admin", "static", "images", "template-previews")
DASH = os.path.join(ROOT, "03-web-admin", "static", "admin_dashboard.html")

results = []


def rec(vid, ok, detail):
    results.append((vid, ok, detail))
    print("[%s] %-4s %s" % ("PASS" if ok else "FAIL", vid, detail))


def http(path, method="GET", data=None, headers=None, follow=True):
    url = BASE + path
    req = urllib.request.Request(url, method=method, data=data)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    op = urllib.request.build_opener()
    if not follow:
        class NoRedir(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None
        op = urllib.request.build_opener(NoRedir)
    try:
        r = op.open(req, timeout=15)
        # ★★★ T26 / R3-1（判据自身 bug 修复，2026-10-02）：
        #   原实现返回 `dict(r.headers)`，而 `dict()` 转换【丢失 HTTP 头的大小写
        #   不敏感性】—— 键变成服务端发出的原始大小写（实测为全小写
        #   `content-type`），于是 `:82` 的 `h.get("Content-Type")` 恒为 None
        #   ⇒ V2 把【正常响应】误判为 FAIL。
        #
        #   实测对照（同一响应）：
        #     r.headers.get('Content-Type')          = 'image/png'   ✅
        #     dict(r.headers).get('Content-Type')    = None          ❌（原路径）
        #     dict(r.headers).get('content-type')    = 'image/png'   ✅
        #
        #   ⇒ 现改为返回一个【大小写不敏感】的映射包装，保留调用方签名不变。
        #   ── 原实现（留痕，勿删）──────────────────────────────────
        #      return r.status, dict(r.headers), r.read()
        #   ─────────────────────────────────────────────────────────
        return r.status, _CIHeaders(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, _CIHeaders(e.headers), e.read()


class _CIHeaders:
    """★ 大小写不敏感的 header 映射（dict 语义，但 .get() 不区分大小写）。

    保留 dict 的其它行为（keys/items/__contains__），避免影响既有调用方。
    """

    def __init__(self, headers):
        self._h = headers
        self._d = dict(headers)

    def get(self, key, default=None):
        # 先按原键取（HTTPMessage 本身就不区分大小写）
        try:
            v = self._h.get(key)
        except Exception:
            v = None
        if v is not None:
            return v
        # 兜底：遍历 dict 做不区分大小写的匹配
        kl = key.lower()
        for k, vv in self._d.items():
            if k.lower() == kl:
                return vv
        return default

    def __getitem__(self, key):
        v = self.get(key, None)
        if v is None:
            raise KeyError(key)
        return v

    def __contains__(self, key):
        return self.get(key, None) is not None

    def keys(self):
        return self._d.keys()

    def items(self):
        return self._d.items()

    def __iter__(self):
        return iter(self._d)

    def __repr__(self):
        return repr(self._d)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 16), b""):
            h.update(blk)
    return h.hexdigest()


# ---------------------------------------------------------------- V1
def v1():
    s = open(DASH, "rb").read().decode("utf-8")
    refs = sorted(set(re.findall(r"/images/template-previews/[^\"')\s>]+", s)))
    miss = []
    print("  -- V1 逐路径存在性表（引用 %d 个）--" % len(refs))
    for r in refs:
        p = os.path.join(ROOT, "03-web-admin", "static",
                         r.lstrip("/").replace("/", os.sep))
        ex = os.path.isfile(p)
        if not ex:
            miss.append(r)
        print("     %-46s %s %s" % (r, "EXISTS" if ex else "MISSING",
                                    ("%d B" % os.path.getsize(p)) if ex else ""))
    rec("V1", len(refs) == 19 and not miss,
        "引用 %d 个，缺失 %d 个" % (len(refs), len(miss)))


# ---------------------------------------------------------------- V2/V3/V4
def v2():
    st, h, b = http("/images/template-previews/vodex.png")
    ct = h.get("Content-Type", "")
    ok = st == 200 and ct == "image/png" and b[:8] == b"\x89PNG\r\n\x1a\n"
    rec("V2", ok, "GET vodex.png -> %s CT=%r bytes=%d" % (st, ct, len(b)))


def v3():
    # 抽样 3 个：跨 3 个不同模板 + 跨 css/js
    samples = [
        "/landing-pages/velocx/static/css/all.min.css",
        "/landing-pages/premhd/static/js/main.js",
        "/landing-pages/minidr/static/css/home_v2.css",
    ]
    allok = True
    for s in samples:
        st, h, b = http(s)
        ok = st == 200 and len(b) > 0
        allok &= ok
        print("     %-48s -> %s CT=%r bytes=%d"
              % (s, st, h.get("Content-Type", ""), len(b)))
        # 与磁盘源逐字节比对
        src = os.path.join(ROOT, "04-landing", "assets",
                           "landing-pages__" + s.split("/")[2] + "__static__"
                           + s.split("/")[4] + "__" + s.split("/")[5])
        if os.path.isfile(src):
            same = sha256(src) == hashlib.sha256(b).hexdigest()
            allok &= same
            print("       vs 04-landing 源 sha256 一致: %s" % same)
    rec("V3", allok, "抽样 3 个静态资产均 200 且与源一致")


def v4():
    cases = [
        "/images/../../etc/passwd",
        "/images/..%2f..%2f..%2fetc%2fpasswd",
        "/landing-pages/../../package.json",
        "/images/%2e%2e/%2e%2e/%2e%2e/windows/win.ini",
        "/landing-pages/..%5c..%5cpackage.json",
    ]
    allok = True
    for c in cases:
        st, h, b = http(c)
        # 4xx 才算拒绝
        ok = st is not None and 400 <= st < 500
        allok &= ok
        leak = b"root:" in b or b'"name"' in b or b"[extensions]" in b
        print("     %-52s -> %s %s leak=%s"
              % (c, st, "REJECTED" if ok else "!! NOT REJECTED", leak))
        allok &= not leak
    rec("V4", allok, "5 条穿越向量全部 4xx 且无内容泄露")


def v5():
    # 登录拿 cookie
    body = b"username=admin&password=i1c3-e2e-admin"
    st, h, b = http(ADMIN + "/login", "POST", body,
                    {"Content-Type": "application/x-www-form-urlencoded"},
                    follow=False)
    cookie = ""
    sc = h.get("Set-Cookie", "")
    if isinstance(sc, str):
        sc = [sc] if sc else []
    cookie = "; ".join(c.split(";")[0] for c in (sc or []))
    # 兜底：urllib 在重定向/多头上可能不聚合 Set-Cookie，直接读 raw 头
    if not cookie:
        try:
            import http.client as _hc
            c = _hc.HTTPConnection("127.0.0.1", 3000, timeout=15)
            c.request("POST", ADMIN + "/login", body,
                      {"Content-Type": "application/x-www-form-urlencoded"})
            r = c.getresponse()
            raw = r.getheaders()
            r.read()
            c.close()
            cookie = "; ".join(v.split(";")[0] for k, v in raw
                               if k.lower() == "set-cookie")
        except Exception as e:
            print("     cookie 兜底失败:", e)
    print("     login POST -> %s (302=%s) cookie=%s"
          % (st, st in (302, 303), "yes" if cookie else "no"))

    checks = [
        (ADMIN + "/login", "登录页"),
        (ADMIN + "/dashboard", "面板页"),
        (ADMIN + "/api/stats", "stats API"),
    ]
    allok = True
    for path, label in checks:
        st, h, b = http(path, headers={"Cookie": cookie} if cookie else {})
        ok = st == 200
        allok &= ok
        print("     %-42s %-8s -> %s bytes=%d" % (path, label, st, len(b)))
    rec("V5", allok, "login/dashboard/api-stats 全部 200")


# ---------------------------------------------------------------- V6/V7
def v6v7():
    before = json.load(open(os.path.join(ROOT, "_t21_work", "baseline_before.json"),
                            encoding="utf-8"))
    # V6: 04-landing 全量比对
    diff = []
    cur = {}
    for dp, dn, fns in os.walk(os.path.join(ROOT, "04-landing")):
        for fn in fns:
            p = os.path.join(dp, fn)
            cur[os.path.relpath(p, ROOT)] = sha256(p)
    b4 = before["04-landing"]
    for k in sorted(set(b4) | set(cur)):
        if b4.get(k) != cur.get(k):
            diff.append(k)
    rec("V6", not diff, "04-landing %d 文件全量 sha256 比对，变更 %d"
        % (len(b4), len(diff)))
    for d in diff[:10]:
        print("     CHANGED", d)

    # V7: 守护文件
    g = {
        "_manifest.sha256": os.path.join(ROOT, "_manifest.sha256"),
        "contracts.md": os.path.join(ROOT, "09-docs", "spec", "contracts.md"),
    }
    allok = True
    for k, p in g.items():
        same = sha256(p) == before[k]
        allok &= same
        print("     %-20s %s" % (k, "UNCHANGED" if same else "!! CHANGED"))
    # 顺带核硬约束：未改 dashboard html / landing.js / app.js
    #
    # ★★★ T26 / R3-1（Owner 授权翻转期望，2026-10-02）：
    #   `app.js` 于 T26·R2-5 被【有意修改】（`/healthz` 从静态常量改为
    #   真实依赖检查：MongoDB readyState + Redis PING + Go /health）。
    #   ⇒ 本脚本原先要求 `app.js` UNCHANGED 属【T21 时点的冻结】，
    #     已与当前基线不符 ⇒ 会把【合法变更】误报为 RED。
    #
    #   ⇒ 翻转后的口径：
    #     · `_manifest.sha256` / `contracts.md` / `admin_dashboard.html` /
    #       `landing.js` —— **仍然必须 UNCHANGED**（真正的硬约束）
    #     · `app.js` —— **允许变更**，但必须【仍是健康检查的真实实现】
    #       （即不得被改回静态常量）⇒ 用内容断言替代哈希断言。
    #   ★ 保留原冻结表于注释，以便溯源。
    #   ── 原冻结表（留痕，勿删）─────────────────────────────────
    #      frozen = {
    #          "admin_dashboard.html": ...,
    #          "landing.js": ...,
    #          "app.js": ...,           # ★ T26 后不再冻结
    #      }
    #   ───────────────────────────────────────────────────────────
    frozen = {
        "admin_dashboard.html": os.path.join(ROOT, "03-web-admin", "static",
                                             "admin_dashboard.html"),
        "landing.js": os.path.join(ROOT, "02-backend-node", "src_restored",
                                   "plugins", "api", "routes", "landing.js"),
    }
    for k, p in frozen.items():
        same = sha256(p) == before[k]
        allok &= same
        print("     硬约束 %-22s %s" % (k, "UNCHANGED" if same else "!! CHANGED"))

    # ★ T26：app.js 改为【内容断言】——
    #   必须仍是健康检查的真实实现（含依赖探测），且不含静态常量写法。
    appjs = os.path.join(ROOT, "02-backend-node", "src_restored", "app.js")
    try:
        with open(appjs, "r", encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except Exception:
        src = ""
    has_real_health = ("readyState" in src and "ping" in src.lower())
    # ★ 静态常量写法：fastify.get('/healthz', async () => ({ status: 'ok' }))
    import re as _re
    stale = _re.search(
        r"fastify\.get\(\s*['\"]/healthz['\"]\s*,\s*async\s*\(\s*\)\s*=>\s*\(\s*\{\s*status:\s*['\"]ok['\"]",
        src)
    ok_app = has_real_health and not stale
    allok &= ok_app
    print("     硬约束 %-22s %s（T26 后改为内容断言：真实依赖检查=%s，静态常量=%s）"
          % ("app.js", "OK" if ok_app else "!! FAIL", has_real_health, bool(stale)))

    rec("V7", allok,
        "_manifest.sha256 / contracts.md / admin_dashboard.html / landing.js 未改；"
        "app.js 含真实健康检查（T26 后不再冻结哈希）")


def main():
    offline = "--offline" in sys.argv
    print("=== T21 判据验证 (%s) ===" % ("offline" if offline else "online"))
    v1()
    if not offline:
        v2()
        v3()
        v4()
        v5()
    v6v7()
    npass = sum(1 for _, ok, _ in results if ok)
    print("\n=== 汇总: %d/%d PASS ===" % (npass, len(results)))
    for vid, ok, d in results:
        print("  %-4s %s" % (vid, "PASS" if ok else "FAIL"))
    sys.exit(0 if npass == len(results) else 1)


if __name__ == "__main__":
    main()
