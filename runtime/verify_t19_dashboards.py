# -*- coding: utf-8 -*-
"""
T19 后台看板实施 —— 端到端判据 V1..V9。

★ 动前红 / 动后绿。
★ 只读：本脚本不改任何文件、不写任何数据。

判据：
  V1  GET /api/dashboard/device-versions （带 token）⇒ 200 且 data.length >= 4
  V2  GET /api/dashboard/collect-summary （带 token）⇒ 200 且 total >= 6
  V3  两端点【无 token】⇒ 401
  V4  前端两页面存在
  V5  dist 已重新构建（文件数 > 0）
  V6  既有端点未回归：/api/devices、/api/collect/stats、/api/dashboard 全部 200
  V7  未改 01-backend-go/**、landing.js、app.js   （由外部 sha 比对，见 V7 段落）
  V8  collect-summary 响应含 limitation 字段（非空字符串）
  V9  守护：_manifest.sha256、contracts.md 未改（由外部比对，见 V9 段落）

★ V1 的 data.length >= 4 是"有真实数据"的机械证据。
★ V8 是"未假装合并"的证据。
"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib
import http.cookiejar as http_cookiejar
import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("T19_BASE", "http://127.0.0.1:3000")
ROOT = USDT_ROOT
ADMIN_USER = "admin"
ADMIN_PASS = "i1c3-e2e-admin"

results = []


def check(vid, ok, detail):
    results.append((vid, bool(ok), detail))
    print("[%s] %s  %s" % ("PASS" if ok else "FAIL", vid, detail))


def http(method, path, body=None, cookie=None, timeout=30):
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if cookie:
        req.add_header("Cookie", cookie)
    opener = urllib.request.build_opener()
    try:
        with opener.open(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return -1, "EXC: %r" % (e,)


def login():
    # ★ 注意：不能把局部变量命名为 http（会遮蔽模块级 http() 函数）
    cj = http_cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    req = urllib.request.Request(
        BASE + "/api/auth/login",
        data=json.dumps({"username": ADMIN_USER, "password": ADMIN_PASS}).encode(),
        method="POST",
    )
    req.add_header("Content-Type", "application/json")
    with opener.open(req, timeout=30) as resp:
        body = resp.read().decode("utf-8", "replace")
    tok = None
    for c in cj:
        if c.name == "accessToken":
            tok = c.value
    return tok, body


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    print("=" * 72)
    print("T19 后台看板验证  base=%s" % BASE)
    print("=" * 72)

    # ---------- 登录 ----------
    try:
        tok, lbody = login()
    except Exception as e:  # noqa: BLE001
        print("LOGIN EXCEPTION: %r" % (e,))
        check("LOGIN", False, "admin 登录失败，后续判据无法进行")
        summary()
        return
    print("LOGIN 200, token=%s..., body=%s" % ((tok or "")[:16], lbody[:160]))
    cookie = "accessToken=" + tok if tok else None
    if not tok:
        check("LOGIN", False, "未取得 accessToken cookie")
        summary()
        return

    # ---------- V1 ----------
    s, b = http("GET", "/api/dashboard/device-versions", cookie=cookie)
    print("\n--- V1 raw status=%s ---" % s)
    print(b[:2000])
    ok1 = False
    d1 = None
    if s == 200:
        try:
            j = json.loads(b)
            arr = j.get("data")
            if isinstance(arr, list):
                d1 = arr
                ok1 = len(arr) >= 4
            detail = "status=200 data.length=%s" % (len(arr) if isinstance(arr, list) else "NOT_A_LIST")
        except Exception as e:  # noqa: BLE001
            detail = "status=200 但 JSON 解析失败: %r" % (e,)
    else:
        detail = "status=%s body=%s" % (s, b[:200])
    check("V1", ok1, "device-versions 带 token ⇒ " + detail)

    # ---------- V2 ----------
    s, b = http("GET", "/api/dashboard/collect-summary", cookie=cookie)
    print("\n--- V2 raw status=%s ---" % s)
    print(b[:2000])
    ok2 = False
    d2 = None
    if s == 200:
        try:
            j = json.loads(b)
            d2 = j.get("data")
            total = d2.get("total") if isinstance(d2, dict) else None
            ok2 = isinstance(total, (int, float)) and total >= 6
            detail = "status=200 data.total=%s" % (total,)
        except Exception as e:  # noqa: BLE001
            detail = "status=200 但 JSON 解析失败: %r" % (e,)
    else:
        detail = "status=%s body=%s" % (s, b[:200])
    check("V2", ok2, "collect-summary 带 token ⇒ " + detail)

    # ---------- V3 ----------
    e1s, e1b = http("GET", "/api/dashboard/device-versions")
    e2s, e2b = http("GET", "/api/dashboard/collect-summary")
    print("\n--- V3 无 token ---")
    print("device-versions  -> %s %s" % (e1s, e1b[:150]))
    print("collect-summary  -> %s %s" % (e2s, e2b[:150]))
    check("V3", e1s == 401 and e2s == 401,
          "device-versions=%s, collect-summary=%s（须均 401）" % (e1s, e2s))

    # ---------- V8 ----------
    #
    # ★★★ T26 / R3-1（Owner 授权翻转期望，2026-10-02）：
    #   原断言（T19 时期）：`limitation` 必须是【非空字符串】。
    #     当时的背景：collect-summary 只聚合 gasleak 一侧 ⇒ 必然存在数据局限 ⇒
    #     用 non-empty limitation 提示"未合并"。
    #
    #   ★ 变更依据：T22 落地【跨库真合并】（Go 侧新增 `/app/bill-list`，
    #     Node 侧 fetchQiankeBillTotal() 真合并 gasleak + qianke）
    #     ⇒ `sources = {gasleak:6, qianke:33}`、`scope = "gasleak+qianke"`，
    #       而 `limitation` 变为 **null**（表示"无局限"）。
    #     ⇒ 实测（T22 端到端）：`limitation:null` 是【正确值】。
    #
    #   ⇒ 翻转后的断言：`limitation` 必须为 None（无局限），
    #     且【同时】要求 `scope` 表明已合并（防止退化成"静默降级"）。
    #   ★ 保留原断言文本于注释，以便溯源。
    #   ── 原断言（留痕，勿删）────────────────────────────────────
    #      ok8 = isinstance(lim, str) and len(lim.strip()) > 0
    #      check("V8", ok8, "collect-summary.data.limitation = %r" % (lim,))
    #   ───────────────────────────────────────────────────────────
    lim = None
    scope = None
    if isinstance(d2, dict):
        lim = d2.get("limitation")
        scope = d2.get("scope")
    # ★ 翻转：limitation 应为 None（无局限）
    ok8 = (lim is None)
    # ★ 且 scope 必须表明两侧已合并（否则说明静默降级、并非真合并）
    ok8 = ok8 and (scope == "gasleak+qianke")
    print("\n--- V8 limitation=%r scope=%r ---" % (lim, scope))
    check("V8", ok8,
          "collect-summary.data.limitation = %r（★ T22 后期望 None = 无局限），"
          "scope = %r（★ 期望 'gasleak+qianke'）" % (lim, scope))

    # ---------- V6 回归 ----------
    print("\n--- V6 回归（既有端点）---")
    reg = {}
    for p in ["/api/devices", "/api/collect/stats", "/api/dashboard"]:
        ss, bb = http("GET", p, cookie=cookie)
        reg[p] = ss
        print("  %-24s -> %s  %s" % (p, ss, bb[:110]))
    check("V6", all(v == 200 for v in reg.values()), "既有端点状态码=%s" % reg)

    # ---------- V4 前端页面存在 ----------
    print("\n--- V4 前端页面 ---")
    pages = [
        os.path.join(ROOT, r"03-web-admin\src\view\dashboard\deviceVersions\deviceVersions.vue"),
        os.path.join(ROOT, r"03-web-admin\src\view\dashboard\collectSummary\collectSummary.vue"),
    ]
    ex = [os.path.isfile(p) for p in pages]
    for p, e in zip(pages, ex):
        print("  %s  exists=%s" % (p, e))
    check("V4", all(ex), "两页面均存在=%s" % all(ex))

    # ---------- V5 dist ----------
    dist = os.path.join(ROOT, r"03-web-admin\dist")
    n = 0
    if os.path.isdir(dist):
        for _r, _d, fs in os.walk(dist):
            n += len(fs)
    print("\n--- V5 dist ---")
    print("  %s  files=%d" % (dist, n))
    check("V5", n > 0, "dist 文件数=%d（须 >0，实际构建 EXIT 见执行记录）" % n)

    # ---------- V7 禁改文件 ----------
    print("\n--- V7 禁改路径（mtime 抽查）---")
    guard = [
        os.path.join(ROOT, r"02-backend-node\src_restored\app.js"),
        os.path.join(ROOT, r"02-backend-node\src_restored\plugins\api\routes\landing.js"),
    ]
    for g in guard:
        print("  %s  mtime=%s" % (g, _mtime(g)))

    # ---------- V9 守护 ----------
    print("\n--- V9 守护文件 sha256 ---")
    for g in [os.path.join(ROOT, "_manifest.sha256"),
              os.path.join(ROOT, r"09-docs\spec\contracts.md")]:
        print("  %s  sha256=%s" % (g, _sha(g)))

    summary()


def _mtime(p):
    try:
        return __import__("datetime").datetime.fromtimestamp(os.path.getmtime(p)).isoformat()
    except OSError:
        return "MISSING"


def _sha(p):
    try:
        return sha256_file(p)
    except OSError:
        return "MISSING"


def summary():
    print("\n" + "=" * 72)
    for vid, ok, detail in results:
        print("%-4s %s  %s" % (vid, "PASS" if ok else "FAIL", detail[:110]))
    # ★ 任一判据 FAIL ⇒ RED。特别地 LOGIN 失败绝不允许假绿。
    allok = bool(results) and all(ok for _v, ok, _d in results)
    print("-" * 72)
    print("T19_VERIFY_EXIT=%d  (%s)" % (0 if allok else 1, "GREEN" if allok else "RED"))
    print("=" * 72)
    return 0 if allok else 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    rc = main()
    sys.exit(rc if rc is not None else (0 if all(r[1] for r in results) else 1))
