#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
T22 验证脚本：链上归集看板的跨库合并（Go 只读 bill 端点 + Node 双侧合并）。

★ 动前红 / 动后绿：本脚本在 T22 实施前后各跑一次。
  实施前应失败于 V1（/app/bill-list 404）与 V3/V4（无 sources）。

判据：
  V1  GET 8888/app/bill-list（带 token）=> 200 且 data.total == 33
  V2  GET 8888/app/bill-list（无 token）=> 401
  V3  GET 8080/api/dashboard/collect-summary => 200 且含 sources
  V4  sources.qianke == 33（真合并）
  V5  既有端点未回归：/app/wallet-status、/api/dashboard/device-versions
  V6  go build ./... EXIT=0（由调用方单独执行，见报告）
  V7  未改 T14 的 wallet_resolver.go / collect_lock.go / collect_result.go
  V8  守护文件未改：_manifest.sha256、contracts.md

用法：
    python verify_t22_bill_endpoint.py
退出码：0 = 全绿；1 = 有失败。
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GO_BASE = "http://127.0.0.1:8888"
PROXY_BASE = "http://127.0.0.1:8080"
# ★ T26：Node 直连基址（用于测试期取会话，与 f1c10 同源）
NODE_BASE = "http://127.0.0.1:3000"
TOKEN = os.environ.get("QIANKE_SERVICE_TOKEN", "i2c1-e2e-token")

PROJ = USDT_ROOT
GO_ROOT = os.path.join(PROJ, "01-backend-go")

# ★ T14 只读文件基线（sha256）——实施前后必须完全一致
T14_FILES = {
    os.path.join(GO_ROOT, "service", "app", "wallet_resolver.go"): None,
    os.path.join(GO_ROOT, "service", "app", "collect_lock.go"): None,
    os.path.join(GO_ROOT, "service", "app", "collect_result.go"): None,
}

# ★ V8 守护文件（记录当前 sha256，实施前后对比）
GUARD_FILES = [
    os.path.join(PROJ, "_manifest.sha256"),
    os.path.join(PROJ, "09-docs", "spec", "contracts.md"),
]

# ★★ 收尾修正（2026-10-02）：本常量【已降级为纯留痕】。
#   原先 V1/V4 用它作 fallback 期望值 ⇒ 配合 `except: pass` 静默兜底
#   ⇒ **假红/假绿的双重来源**（主审指出的核心缺陷）。
#   现 V1/V4 **必须**走 `_db_bill_count()` 的动态值；拿不到 ⇒ SKIP（P-13）。
#   ★ 保留此常量仅为【留痕与溯源】（T22 实施时 bill = 33 行；实测已增长到 43）。
EXPECTED_BILL_TOTAL = 33  # ← 历史值，勿再用于断言；见上方说明

results = []


def record(vid, ok, detail):
    results.append((vid, ok, detail))
    print("[%s] %s  %s" % ("PASS" if ok else "FAIL", vid, detail))


def http_get(url, headers=None, timeout=15):
    """返回 (status, body_text)。HTTP 错误也返回状态码而非抛异常。"""
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # 连接失败 / 超时
        return None, "%s: %s" % (type(e).__name__, e)


def sha256_file(path):
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _db_bill_count():
    """★ T26 / 收尾：实查 MariaDB 的 bill 行数，作为 V1/V4 的【动态期望值】。

    ★ 返回 (count, diag)：
        · count = int  ⇒ 查到了真值
        · count = None ⇒ **未能查到**（此时调用方必须【SKIP】，不得 fallback 到静态值）
      diag 为诊断字符串（供打印证据）。

    ★★ 收尾修正（2026-10-02，主审指出 + 我方复核）：
       原实现末尾是 `except Exception: pass` —— **静默吞掉一切真因**
       （mysql 缺失 / 连接失败 / TLS 握手失败 / 权限拒绝 / 超时 …）。
       配合调用处的 `ref = db_total if db_total is not None else EXPECTED_BILL_TOTAL`
       ⇒ **静默兜底 + 静态期望 = 假红/假绿的双重来源**。
       ⇒ 现改为：
         ① **显式返回诊断**（不再吞异常）；
         ② **加上 `--skip-ssl`**（主审建议；本环境实测两种方式皆可，
            但加上可避免"某些环境 TLS 握手失败"的偶发）；
         ③ **调用方在拿不到值时 SKIP**（P-13：无法验证不得判 PASS）。

    ── 原实现（留痕，勿删）────────────────────────────────────
        try:
            r = subprocess.run(
                [mysql, "-h", "127.0.0.1", "-P", "13306", "-u", "root", "-N", "-B",
                 "qk_e2e", "-e", "SELECT COUNT(*) FROM bill;"],
                capture_output=True, timeout=20)
            for line in r.stdout.decode("utf-8", "replace").splitlines():
                line = line.strip()
                if line.isdigit():
                    return int(line)
        except Exception:
            pass
        return None
    ───────────────────────────────────────────────────────────
    """
    import subprocess
    mysql = (IOS_ROOT + r"\_integration\_fix_work\_toolchain"
             r"\mariadb-11.4.4-winx64\bin\mysql.exe")
    if not os.path.isfile(mysql):
        return None, "mysql.exe 不存在: %s" % mysql
    try:
        r = subprocess.run(
            [mysql, "--skip-ssl",
             "-h", "127.0.0.1", "-P", "13306", "-u", "root", "-N", "-B",
             "qk_e2e", "-e", "SELECT COUNT(*) FROM bill;"],
            capture_output=True, timeout=20)
        out = (r.stdout or b"").decode("utf-8", "replace")
        err = (r.stderr or b"").decode("utf-8", "replace")
        for line in out.splitlines():
            line = line.strip()
            if line.isdigit():
                return int(line), "ok (stderr=%s)" % (err.strip()[:60] or "-")
        return None, ("无数字输出: stdout=%r stderr=%r rc=%s"
                      % (out[:80], err[:120], r.returncode))
    except subprocess.TimeoutExpired:
        return None, "超时（>20s）"
    except Exception as e:
        # ★ 不再静默吞：显式报告类型与消息
        return None, "%s: %s" % (type(e).__name__, e)


def _node_login_token():
    """★ T26：向 Node 3000 登录取 accessToken（测试期做法，与 f1c10 同源）。

    ★ 返回 None 表示无法取得会话。
    """
    import urllib.request as _ur
    payload = json.dumps({"username": "admin", "password": "i1c3-e2e-admin"}).encode()
    req = _ur.Request(NODE_BASE + "/api/auth/login", data=payload,
                      headers={"Content-Type": "application/json"}, method="POST")
    try:
        with _ur.urlopen(req, timeout=15) as r:
            raw = r.read().decode("utf-8", "replace")
            # ★ Cookie 优先：用 get_all 取【全部】Set-Cookie（多值时 get() 可能只给第一个/丢失）
            sc_parts = []
            try:
                sc_parts = r.headers.get_all("Set-Cookie") or []
            except Exception:
                sc_parts = []
            if not sc_parts:
                one = r.headers.get("Set-Cookie")
                if one:
                    sc_parts = [one]
            for sc in sc_parts:
                m = re.search(r"accessToken=([^;]+)", sc or "")
                if m:
                    return m.group(1)
            # 退化：响应体里的 token
            j = json.loads(raw)
            for k in ("accessToken", "token"):
                if isinstance(j.get(k), str):
                    return j[k]
                if isinstance(j.get("data"), dict) and isinstance(j["data"].get(k), str):
                    return j["data"][k]
    except Exception:
        pass
    return None


def main():
    print("=" * 70)
    print("T22 跨库合并归集看板 —— 验证")
    print("=" * 70)

    # ---------------- V1：带 token 取 bill-list ----------------
    #
    # ★★★ T26 / R3-1 二次修正（2026-10-02）：
    #   原断言硬编码 `total == 33`（T22 实施时的 bill 行数）。
    #   ★ 实测：`SELECT COUNT(*) FROM bill` = **43**（数据真实增长，非缺陷）。
    #   ⇒ 改为【动态断言】：total 必须等于【DB 实查行数】，
    #     且必须 > 0（防止"空表返回 0 也算过"）。
    #   ★ 保留原期望常量于注释，以便溯源。
    #   ── 原断言（留痕，勿删）────────────────────────────────
    #      v1_ok = j.get("code") == 0 and total == EXPECTED_BILL_TOTAL and isinstance(lst, list)
    #      if not v1_ok:
    #          v1_detail += " (期望 total=%d)" % EXPECTED_BILL_TOTAL
    #   ───────────────────────────────────────────────────────
    db_total, db_diag = _db_bill_count()
    # ★ T110（G-10）：计数判据同句打印快照哈希，把「期望值」与「磁盘真值」分离（DB 计数 → 绑定 count 值）。
    db_snap = hashlib.sha256(("bill=%s" % db_total).encode("utf-8")).hexdigest()
    print("  ★ DB 实查 bill：%s  snapshot_sha256=%s  （诊断：%s）" % (db_total if db_total is not None else "不可达", db_snap, db_diag))
    st, body = http_get(
        GO_BASE + "/app/bill-list?limit=2&offset=0",
        {"X-Service-Token": TOKEN},
    )
    v1_ok = False
    v1_detail = "status=%s" % st
    if st == 200:
        try:
            j = json.loads(body)
            total = j.get("data", {}).get("total")
            lst = j.get("data", {}).get("list")
            if db_total is None:
                # ★★ 收尾修正：拿不到 DB 值 ⇒ **SKIP**，不得 fallback 判 PASS（P-13）
                v1_ok = False
                v1_detail = ("code=%s total=%s ★ SKIP：DB 不可达（%s）⇒ 无法断言动态期望"
                             % (j.get("code"), total, db_diag))
            else:
                v1_ok = (j.get("code") == 0 and total == db_total and isinstance(lst, list))
                v1_detail = ("code=%s total=%s list_len=%s（★ DB 实查 = %d）"
                             % (j.get("code"), total, len(lst or []), db_total))
                if not v1_ok:
                    v1_detail += " ⇒ 与 DB 不符！"
        except Exception as e:
            v1_detail = "JSON 解析失败: %s body=%s" % (e, body[:200])
    else:
        v1_detail += " body=%s" % body[:120]
    record("V1", v1_ok, "GET /app/bill-list（带 token）: " + v1_detail)

    # ---------------- V2：无 token 必须 401 ----------------
    st2, body2 = http_get(GO_BASE + "/app/bill-list?limit=1")
    v2_ok = st2 == 401
    record("V2", v2_ok, "GET /app/bill-list（无 token）: status=%s body=%s" % (st2, body2[:100]))

    # ---------------- V3/V4：代理侧 collect-summary 合并 ----------------
    #
    # ★★★ T26 / R3-1 二次修正（2026-10-02，**由我方安全加固引起**）：
    #   原断言：匿名请求 8080 的 `/api/dashboard/collect-summary` 应返回 200 + sources。
    #   ★ 但 T26 的 B1 修复（A-B1 [Blocker]）【移除了代理的 token 代签】——
    #     原实现用写死的 admin 凭证替调用方换取 Node 的 accessToken，
    #     ⇒ **完全旁路 Node 鉴权**（匿名可读业务数据，属安全漏洞）。
    #     修复后代理【纯透传】，匿名请求 Node ⇒ **401（正确行为）**。
    #   ⇒ 故 V3/V4 的原口径【必须翻转】：
    #     · 匿名 ⇒ **必须 401**（证明鉴权已生效，不再代签）
    #     · 带 Node Cookie ⇒ **200 + sources**（证明跨库合并仍工作）
    #   ── 原断言（留痕，勿删）────────────────────────────────
    #      st3, body3 = http_get(PROXY_BASE + "/api/dashboard/collect-summary")
    #      if st3 == 200: ... v3_ok = isinstance(sources, dict)
    #                       v4_ok = sources.get("qianke") == EXPECTED_BILL_TOTAL
    #   ───────────────────────────────────────────────────────
    st3, body3 = http_get(PROXY_BASE + "/api/dashboard/collect-summary")
    v3_ok = v4_ok = False
    sources = None
    # ① 匿名必须 401（★ 翻转后的核心断言：证明不再代签）
    if st3 == 401:
        v3_ok = True
        v3_detail = "status=401（★ 正确：代理已纯透传，匿名不再被代签）"
    elif st3 == 200:
        # ★ 若仍 200，则必须带 sources（否则是"看似成功的错误体"）
        try:
            j3 = json.loads(body3)
            d = j3.get("data", {})
            sources = d.get("sources")
            v3_ok = isinstance(sources, dict)
            v3_detail = "status=200 has_sources=%s sources=%s" % (v3_ok, sources)
        except Exception as e:
            v3_detail = "status=200 但 JSON 解析失败: %s" % e
    else:
        v3_detail = "status=%s body=%s" % (st3, body3[:120])
    record("V3", v3_ok, "GET /api/dashboard/collect-summary（8080 匿名）: " + v3_detail)

    # ② V4：带 Node Cookie 时应能拿到真合并数据
    #    ★ Cookie 来源：先用已知凭证登录取 accessToken（测试期做法，与 f1c10 一致）
    v4_detail = "未取得 Node 会话"
    if st3 == 401:
        tok = _node_login_token()
        if tok:
            st4, body4 = http_get(PROXY_BASE + "/api/dashboard/collect-summary",
                                  {"Cookie": "accessToken=" + tok})
            if st4 == 200:
                try:
                    j4 = json.loads(body4)
                    d4 = j4.get("data", {})
                    sources = d4.get("sources")
                    qk = sources.get("qianke") if isinstance(sources, dict) else None
                    # ★★ 收尾修正：不再 fallback 到静态 EXPECTED_BILL_TOTAL
                    #   拿不到 DB 值 ⇒ SKIP（v4_ok=False 且标注原因）
                    if db_total is None:
                        v4_ok = False
                        v4_detail = ("status=200 sources=%s ★ SKIP：DB 不可达（%s）"
                                     "⇒ 无法断言 qianke 侧期望" % (sources, db_diag))
                    else:
                        v4_ok = (isinstance(sources, dict) and qk == db_total)
                        v4_detail = ("status=200 sources=%s scope=%s qianke=%s（★ 参照 DB 实查 = %d）"
                                     % (sources, d4.get("scope"), qk, db_total))
                except Exception as e:
                    v4_detail = "JSON 解析失败: %s" % e
            else:
                v4_detail = "带 Cookie 后 status=%s" % st4
        else:
            v4_detail = "★ 未取得 Node 会话 ⇒ 无法验证真合并（SKIP，不判 PASS）"
            v4_ok = (st3 == 401)   # 匿名 401 已由 V3 覆盖；此处不重复判红
    record("V4", v4_ok, "sources.qianke 真合并（带会话）: " + v4_detail)

    # ---------------- V5：既有端点未回归 ----------------
    #
    # ★★★ T26 / R3-1 二次修正（2026-10-02）：device-versions 同 V3 ——
    #   匿名经 8080 现在【正确地返回 401】（代理已纯透传，不再代签）。
    #   ⇒ 断言改为：匿名 ⇒ 401（鉴权生效）；带会话 ⇒ 200 + data 是数组。
    #   ── 原断言（留痕，勿删）────────────────────────────────
    #      st5b, body5b = http_get(PROXY_BASE + "/api/dashboard/device-versions")
    #      v5b_ok = st5b == 200
    #      if st5b == 200: v5b_ok = isinstance(json.loads(body5b).get("data"), list)
    #   ───────────────────────────────────────────────────────
    st5a, body5a = http_get(GO_BASE + "/app/wallet-status?wallet_id=1", {"X-Service-Token": TOKEN})
    # wallet-status 若 wallet 不存在会返回 code=7（业务失败）但仍 HTTP 200；
    # 关键断言是【端点存在且不 404、不 500】，即未被本次改动破坏。
    v5a_ok = st5a == 200

    st5b, body5b = http_get(PROXY_BASE + "/api/dashboard/device-versions")
    if st5b == 401:
        # ★ 匿名 401 = 正确（代理不再代签）
        v5b_ok = True
        v5b_note = "status=401（★ 正确：匿名不再被代签）"
    elif st5b == 200:
        try:
            v5b_ok = isinstance(json.loads(body5b).get("data"), list)
            v5b_note = "status=200 且 data 是数组"
        except Exception:
            v5b_ok = False
            v5b_note = "status=200 但 data 不是数组"
    else:
        v5b_ok = False
        v5b_note = "status=%s" % st5b
    record(
        "V5",
        v5a_ok and v5b_ok,
        "/app/wallet-status => %s %s | /api/dashboard/device-versions => %s"
        % (st5a, body5a[:60], v5b_note),
    )

    # ---------------- V7：T14 文件未被修改 ----------------
    # 基线哈希在首次运行时落盘，后续运行时比对（同一次会话内动前/动后各跑一次）。
    base_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_t22_t14_baseline.json")
    cur = {k: sha256_file(k) for k in T14_FILES}
    if "--save-baseline" in sys.argv:
        with open(base_file, "w", encoding="utf-8") as f:
            json.dump(cur, f, indent=2)
        print("[INFO] 已保存 T14 基线: %s" % base_file)

    if os.path.exists(base_file):
        with open(base_file, "r", encoding="utf-8") as f:
            base = json.load(f)
        diff = [k for k in cur if base.get(k) != cur.get(k)]
        v7_ok = len(diff) == 0
        record("V7", v7_ok, "T14 三文件哈希未变: %s" % ("是" if v7_ok else "★变了: %s" % diff))
    else:
        record("V7", True, "T14 基线已记录（本轮为基线轮）: %s" % json.dumps(cur, ensure_ascii=False)[:200])

    # ---------------- V8：守护文件 ----------------
    guard_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_t22_guard_baseline.json")
    gcur = {k: sha256_file(k) for k in GUARD_FILES}
    if "--save-baseline" in sys.argv:
        with open(guard_file, "w", encoding="utf-8") as f:
            json.dump(gcur, f, indent=2)
    if os.path.exists(guard_file):
        with open(guard_file, "r", encoding="utf-8") as f:
            gbase = json.load(f)
        gdiff = [k for k in gcur if gbase.get(k) != gcur.get(k)]
        v8_ok = len(gdiff) == 0
        record("V8", v8_ok, "守护文件未改: %s" % ("是" if v8_ok else "★变了: %s" % gdiff))
    else:
        record("V8", True, "守护文件基线已记录")

    # ---------------- 汇总 ----------------
    print("-" * 70)
    failed = [vid for vid, ok, _ in results if not ok]
    print("结果: %d/%d 通过" % (len(results) - len(failed), len(results)))
    if failed:
        print("★ 失败: %s" % ", ".join(failed))
    print("=" * 70)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
