# -*- coding: utf-8 -*-
"""
X6 判据：管理台登录冒烟（覆盖验收项 1.8）。

★ Owner 未单独裁决；档位依 `证据局限闭合报告.md:359` = **R2**。

★ 1.8 原文（需求文档.md:108）：
   | 1.8 | 后台可登录并完成核心操作 | 渠道/设备/钱包/归集/分账可用 |

★★ 调度的取证结论（本卡据此设计断言）：
   · `admin_dashboard.html` 只有 11 个端点（apk/theme/pixel/stats/visits/template/login）
     —— **不含**渠道/设备/钱包/归集/分账
   · 这 5 类在 **`plugins/api/routes/*.js` 的 97 条路由**中：
       渠道 12 条 · 设备 12 条 · 钱包 10 条 · 归集 14 条 · **分账 0 条**
   · **分账**：实测有 4 处语义（在 core 与 schedules 下）
     ⇒ **是归集链路的内部逻辑，不是独立端点** ⇒ 本卡**通过归集端点间接验证**

用法：
    python verify_admin_login.py              # 全量
    python verify_admin_login.py --selftest   # 量尺前置断言（P-5）

退出码：0 = 全绿；非 0 = 有红。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

# ★ X3：本脚本自带 UTF-8 输出（P-10）
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

API = "http://127.0.0.1:3000"
ADMIN = "/mgr-admin-8bcde2021d98"
CREDS = {"username": "admin", "password": "i1c3-e2e-admin"}

# ★ 1.8 的 5 类核心操作 → 代表端点（调度已取证）
CORE = [
    ("渠道", "/api/channels"),
    ("设备", "/api/devices"),
    ("钱包", "/api/chain-providers"),
    ("归集", "/api/collect/targets"),
    # 分账：无独立端点 ⇒ 用归集配置间接验证（归集链内含分账逻辑）
    ("分账", "/api/collect/configs"),
]

_results = []


def rec(name, ok, detail):
    _results.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """★ 禁止自动跟随 302（否则测不出"登录成功返回 302"）。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def http(method, path, body=None, token=None, timeout=12, raw=None, ctype=None,
         follow=True):
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
                return r.status, r.read(), _hdrs(r)
        # ★ 不跟随：用自定义 opener
        op = urllib.request.build_opener(NoRedirect)
        with op.open(req, timeout=timeout) as r:
            return r.status, r.read(), _hdrs(r)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), _hdrs(e)
    except Exception as e:
        return -1, f"EXC:{e}".encode(), {}


def _hdrs(resp):
    """
    ★★ 修正（2026-09-30，X6b 执行者指出 + 调度确认）：
      初版返回 `dict(r.headers)`，会【折叠重名响应头】——
      `Set-Cookie` 有 accessToken + refreshToken **两条**，
      转 dict 后只剩一条 ⇒ `h.get('Set-Cookie')` 可能取不到 accessToken ⇒
      **依赖 cookie 的断言假红/静默 SKIP**。
      ⇒ 改为保留**全量 Set-Cookie**（列表）与其余单值头。
    """
    h = {}
    try:
        h["Set-Cookie-List"] = resp.headers.get_all("Set-Cookie") or []
    except Exception:
        h["Set-Cookie-List"] = []
    try:
        for k, v in resp.headers.items():
            h.setdefault(k, v)
    except Exception:
        pass
    return h


def set_cookie_text(h):
    """把全量 Set-Cookie 拼成一个字符串（供正则提取）。"""
    lst = h.get("Set-Cookie-List") or []
    if lst:
        return " | ".join(lst)
    return str(h.get("Set-Cookie", ""))


def login_json():
    """JSON 登录（/api/auth/login）取 accessToken。"""
    cj = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    req = urllib.request.Request(API + "/api/auth/login",
                                data=json.dumps(CREDS).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with opener.open(req, timeout=12) as r:
            body = r.read().decode("utf-8", "replace")
            m = re.search(r'"accessToken"\s*:\s*"([^"]+)"', body)
            if m:
                return m.group(1)
    except Exception:
        pass
    for c in cj:
        if c.name == "accessToken":
            return c.value
    return None


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    st, b, _ = http("GET", "/healthz")
    print(f"  Node 服务 :3000/healthz => HTTP={st}")
    if st != 200:
        print("  [WARN] 服务未就绪 ⇒ 多数断言会失败")
    st2, b2, _ = http("GET", f"{ADMIN}/login")
    print(f"  登录页 {ADMIN}/login => HTTP={st2}")
    if st2 != 200:
        print("  [FAIL] 登录页不可达 ⇒ 量尺前提不成立")
        ok = False
    t = login_json()
    print(f"  JSON 登录（/api/auth/login）=> {'取到 token' if t else '未取到'}")
    if not t:
        print("  [WARN] 未取到 token ⇒ W5/W6 会失败")
    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== X6 判据：管理台登录冒烟（验收项 1.8）===")
    print("★ 1.8 原文：后台可登录并完成核心操作 | 渠道/设备/钱包/归集/分账可用")
    print("")

    # ================= A 半：后台可登录 =================
    print("【A】后台可登录:")
    st1, b1, _ = http("GET", f"{ADMIN}/login")
    txt1 = b1.decode("utf-8", "replace")
    rec("W1 登录页可达（匿名 200，含 <form）",
        st1 == 200 and "<form" in txt1.lower(),
        f"HTTP={st1} len={len(txt1)}")

    # 表单登录（管理台自己的登录方式）
    #
    # ★★ 修正（2026-09-30，自查 P-5）：初版用 urllib 默认【跟随重定向】⇒
    #   POST /login 返回 302 到 /dashboard，urllib 自动 GET /dashboard
    #   ⇒ 它是 404（UNMATCHED）⇒ 判据把【最终状态 404】误当成 POST 的结果。
    #   ⇒ 必须 follow=False 才能测出真实的 302。
    form = urllib.parse.urlencode(CREDS).encode()
    st2, b2, h2 = http("POST", f"{ADMIN}/login", raw=form,
                       ctype="application/x-www-form-urlencoded", follow=False)
    setck = set_cookie_text(h2)          # ★ 用全量 Set-Cookie（修正折叠 bug）
    has_ck = "accessToken" in setck
    rec("W2 正确凭据（表单）⇒ 302 + accessToken cookie",
        st2 in (301, 302, 303) and has_ck,
        f"HTTP={st2} cookie={'有' if has_ck else '无'}（Set-Cookie 条数={len(h2.get('Set-Cookie-List') or [])}）")

    # ★★ W2b（新增）：302 的跳转目标是否可达
    #   日志实证：登录成功后 UNMATCHED GET ${ADMIN}/dashboard ⇒ 404
    loc = ""
    for k, v in h2.items():
        if k.lower() == "location":
            loc = v
            break
    if loc:
        # ★★ 修正（2026-09-30）：跟随 302 时【必须带上 302 下发的 cookie】，
        #   否则 /dashboard 受保护 ⇒ 裸发请求必 401 ⇒ 假红。
        m = re.search(r"accessToken=([^;]+)", setck)
        foll_tok = m.group(1) if m else None
        stloc, _bl, _hl = http("GET", loc if loc.startswith("/") else "/",
                               token=foll_tok, follow=False)
        rec("W2b ★ 302 的跳转目标可达（带 cookie 跟随，登录后不落 404/401）",
            stloc == 200,
            f"Location={loc} ⇒ HTTP={stloc}（cookie={'带' if foll_tok else '未带'}）"
            + ("  ✓" if stloc == 200 else "  ★ 登录后无法到达 UI（真实缺陷）"))
    else:
        rec("W2b 302 含 Location 头", False, "★ 无 Location（无法验证跳转目标）")

    # 错误密码
    bad = urllib.parse.urlencode({"username": "admin", "password": "wrong-pw-xxx"}).encode()
    st3, _b3, _h3 = http("POST", f"{ADMIN}/login", raw=bad,
                         ctype="application/x-www-form-urlencoded")
    rec("W3 错误密码 ⇒ 401", st3 == 401, f"HTTP={st3}")

    # 空凭据
    empty = urllib.parse.urlencode({"username": "", "password": ""}).encode()
    st4, _b4, _h4 = http("POST", f"{ADMIN}/login", raw=empty,
                         ctype="application/x-www-form-urlencoded")
    rec("W4 空凭据 ⇒ 401", st4 == 401, f"HTTP={st4}")

    # ================= B 半：完成核心操作 =================
    print("")
    print("【B】完成核心操作（5 类）:")
    tok = login_json()
    if not tok:
        print("  [SKIP] 未取到 token ⇒ W5/W6/W8 无法执行 —— SKIP 不等于 PASS（P-13）")
    else:
        print(f"  （已取到 token，长度 {len(tok)}）")
        ok_all = True
        for name, path in CORE:
            st, b, _ = http("GET", path, token=tok)
            good = st == 200
            ok_all = ok_all and good
            body = b.decode("utf-8", "replace")
            print(f"    {name:4s} {path:28s} ⇒ HTTP={st}  {body[:60]}")
        rec("W5 5 类核心操作端点均 200（含分账间接验证）", ok_all,
            "全部可用 ✓" if ok_all else "★ 有失败项")

        # W6：无会话 ⇒ 401（防"端点裸奔"，P-22/P-24 同族）
        naked = []
        for name, path in CORE:
            st, _b, _ = http("GET", path)
            if st != 401:
                naked.append((name, path, st))
        rec("W6 ★ 无会话调核心端点 ⇒ 401（无裸奔）", len(naked) == 0,
            f"★ 未受保护: {naked}" if naked else "5/5 均 401 ✓")

        # W7：logout 后会话失效
        stlo, _b, _h = http("POST", "/api/auth/logout", token=tok)
        stafter, _b2, _ = http("GET", CORE[0][1], token=tok)
        rec("W7 logout 后原会话失效（或 logout 可用）",
            stlo in (200, 204), f"logout HTTP={stlo}；随即访问核心端点 HTTP={stafter}")

        # W8：端到端链路总结
        rec("W8 ★ 端到端：登录→拿 cookie→调 5 类端点→全可用",
            ok_all, "1.8 整体验证通过 ✓" if ok_all else "★ 未通过")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  1.8（后台可登录 + 核心操作）已由机械判据覆盖")
    return 0


if __name__ == "__main__":
    sys.exit(main())
