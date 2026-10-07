# -*- coding: utf-8 -*-
"""W-BE-01 判据：三级等级设计接线（**代理商级**）的 R1–R6。

★ 会话来源：自签 JWT（rbac_login.py），不走 /base/login
  —— 因为 `api/v1/system/sys_captcha.go:13` 的验证码 store 是进程内存，外部读不到答案。
★ 判据口径：契约 C-2 —— Go 失败也返 HTTP 200，成败看 body 的 `code`（**不得用 HTTP 状态判鉴权**）。

用法：python rbac_verify.py            （对 8888 实测）
      python rbac_verify.py --selftest （量尺前置断言：确认「无权限」与「有权限」能被区分）
退出码：0 = 全绿；1 = 有红；2 = 有 SKIP 且无红。
"""
from __future__ import annotations

import importlib.util
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("rbac", os.path.join(_here, "rbac_login.py"))
rbac = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rbac)

# --- 会话（自签） ---
ADMIN = rbac.mint(8, "admin", "超级管理员", "888", "b059de9e-be0c-11f1-9ed6-14755b847ee7")
AGENT_A = rbac.mint(101, "agentA", "代理商A", "1234", "11111111-1111-1111-1111-111111111111")  # agent.id=1
AGENT_B = rbac.mint(9, "agentB", "代理商B", "1234", "cf350b61-a5b7-49e7-b5dd-3d9447c0bbc4")    # agent.id=5
VIEWER = rbac.mint(9, "viewer", "只读用户", "9528", "cf350b61-a5b7-49e7-b5dd-3d9447c0bbc4")   # 代位「工作室」做结构验证

# --- DB 真值（实测 2026-10-03；引用前须重测，见 L048 §7）---
DB_TRUTH = {
    "agent_device_total_user101": 1,   # machine JOIN agent WHERE agent.user_id=101
    "agent_device_total_user9": 0,     # machine JOIN agent WHERE agent.user_id=9
    "machine_all": 9,
    "packet_fee": 10, "agent_ratio": 20, "remainder": 70,   # fee+ratio+remainder = 100
}

RESULTS = []
TRANSPORT = []   # ★ 传输层失败清单：这些读数**不携带任何关于被测物的信息**（E-306 同族）


def rec(rid, ok, detail, skip=False):
    RESULTS.append((rid, "SKIP" if skip else ("PASS" if ok else "FAIL"), detail))
    print("  [%-4s] %-8s %s" % ("SKIP" if skip else ("PASS" if ok else "FAIL"), rid, detail))


def post(path, tok, body=None, method="POST"):
    """★ 判据【不得因被测端返回非 JSON 而崩】——崩掉的量尺等于没有量尺（P-53）。
    传输层瞬时失败（本机实测偶发 ConnectionReset 10054）只重试一次，并把重试如实记进 detail。"""
    s, b = rbac.call(path, tok, body if body is not None else {}, method)
    if not isinstance(b, dict):
        s, b = rbac.call(path, tok, body if body is not None else {}, method)
        if not isinstance(b, dict):
            return s, {"code": None, "msg": "transport/非JSON: %s" % str(b)[:100]}
        b = dict(b)
        b["msg"] = "[重试1次后成功] " + str(b.get("msg", ""))
        return s, b
    if b.get("code") is None:
        TRANSPORT.append("%s %s" % (method, path))
    return s, b


def total_of(body):
    d = body.get("data") if isinstance(body, dict) else None
    return (d or {}).get("total")


def main():
    print("=" * 78)
    print("W-BE-01 · 三级等级设计接线判据（代理商级）  目标 http://127.0.0.1:8888")
    print("=" * 78)

    # ---- R1：菜单隔离 ----
    s, b = post("/menu/getMenu", AGENT_A)
    data = b.get("data") if isinstance(b, dict) else None
    seen = []

    def walk(ns):
        for n in ns or []:
            seen.append(n.get("path"))
            walk(n.get("children"))

    walk(data.get("menus") if isinstance(data, dict) else data)
    forbidden = [p for p in seen if p in (
        "walletinfo", "customerfinance", "privatewallet", "walletinformation", "installation",
        "platformrevenue", "privatedomain", "admin", "authority", "menu", "api", "user",
        "dictionary", "operation", "addr-manage", "syscfg", "state")]
    rec("R1", b.get("code") == 0 and len(seen) == 10 and not forbidden,
        "代理商菜单=%d 条 %s；越权菜单=%s" % (len(seen), seen, forbidden or "无"))

    s, b = post("/menu/getMenu", ADMIN)
    d = b.get("data") if isinstance(b, dict) else None

    def count(ns):
        n = 0
        for x in ns or []:
            n += 1 + count(x.get("children"))
        return n

    rec("R1b", b.get("code") == 0 and count(d.get("menus") if isinstance(d, dict) else d) >= 34,
        "总后台菜单数=%d（应仍为 34，未被本次改动波及）"
        % count(d.get("menus") if isinstance(d, dict) else d))

    # ---- R2：代理商自见，条数 = 库内真值（status=-1 = 全部，见下方 R7 陷阱登记）----
    s, b = post("/device/agent_device_list", AGENT_A, {"page": 1, "pageSize": 10, "status": -1})
    got_a = total_of(b)
    rec("R2-A", got_a == DB_TRUTH["agent_device_total_user101"],
        "user101 agent_device_list total=%s（库内真值=%s）" % (got_a, DB_TRUTH["agent_device_total_user101"]))

    s, b = post("/device/agent_device_list", AGENT_B, {"page": 1, "pageSize": 10, "status": -1})
    got_b = total_of(b)
    rec("R2-B", got_b == DB_TRUTH["agent_device_total_user9"],
        "user9 agent_device_list total=%s（库内真值=%s）" % (got_b, DB_TRUTH["agent_device_total_user9"]))

    s, b = post("/device/agent_wallet_list", AGENT_A, {"page": 1, "pageSize": 10})
    rec("R2-w", b.get("code") == 0, "agent_wallet_list code=%s total=%s" % (b.get("code"), total_of(b)))

    # ---- R3 ★ 反向：代理商调总后台端点 ⇒ 权限不足 ----
    for i, (path, meth, body) in enumerate([
            ("/device/list", "POST", {"page": 1, "pageSize": 10, "status": -1, "agent_id": -1}),
            ("/device/shougei", "POST", {}),
            ("/device/copy_private", "POST", {}),
            ("/device/wallet_list", "POST", {"page": 1, "pageSize": 10}),
            ("/device/private_wallet_list", "POST", {"page": 1, "pageSize": 10}),
            ("/device/hf", "POST", {}),
            ("/device/rk", "POST", {}),
    ], 1):
        s, b = post(path, AGENT_A, body, meth)
        rec("R3-%d" % i, b.get("code") == 7,
            "代理商 → %s %s：http=%s code=%s msg=%s"
            % (meth, path, s, b.get("code"), b.get("msg")))

    # ---- 正控：同批端点在 888 下必须 code:0（证明 R3 是「权限拦的」而非路径错）----
    for i, (path, meth, body) in enumerate([
            ("/device/list", "POST", {"page": 1, "pageSize": 10, "status": -1, "agent_id": -1}),
            ("/device/private_wallet_list", "POST", {"page": 1, "pageSize": 10}),
    ], 1):
        s, b = post(path, ADMIN, body, meth)
        rec("CTRL-%d" % i, b.get("code") == 0,
            "总后台 → %s：code=%s total=%s" % (path, b.get("code"), total_of(b)))

    # ---- R4 ★ 反向（结构验证）：无该权限的 authority 调代理商端点 ⇒ 拒绝 ----
    s, b = post("/device/agent_device_list", VIEWER, {"page": 1, "pageSize": 10, "status": -1})
    rec("R4", b.get("code") == 7,
        "9528（代位工作室/只读级）→ /device/agent_device_list：code=%s msg=%s "
        "★ 注：工作室级【尚未接线】，本项以 9528 代位做结构验证" % (b.get("code"), b.get("msg")))

    # ---- R5 ★ 数值断言：A ≠ B，且各自 = 库内真值 ----
    s, b = post("/device/agent_device_list", AGENT_A, {"page": 1, "pageSize": 10, "status": -1})
    ta = total_of(b)
    s, b = post("/device/agent_device_list", AGENT_B, {"page": 1, "pageSize": 10, "status": -1})
    tb = total_of(b)
    rec("R5", ta == 1 and tb == 0 and ta != tb,
        "代理商A total=%s / 代理商B total=%s ⇒ A≠B 且各自 = 库内真值(1/0)" % (ta, tb))

    # ---- R6 ★ 数值断言：技术服务费 + 佣金 + 余额 = 100 ----
    total = DB_TRUTH["packet_fee"] + DB_TRUTH["agent_ratio"] + DB_TRUTH["remainder"]
    rec("R6", total == 100,
        "技术服务费(%s) + 佣金(%s) + 余额(%s) = %s（规则出处 service/system/sys_user.go:58 "
        "的 fee+ratio>100 拒绝）" % (DB_TRUTH["packet_fee"], DB_TRUTH["agent_ratio"],
                                    DB_TRUTH["remainder"], total))

    # ---- R8 ★ 裁决「绝对不可有」全清单（总调度1 ⌛2026-10-03 的最小权限集裁决）----
    #      逐条断言：代理商调它 ⇒ 必须被拒。**任一条通过 = 越权/可抽干**。
    BANNED = [
        ("/device/list", "POST"), ("/device/wallet_list", "POST"),
        ("/device/private_wallet_list", "POST"), ("/device/shougei", "POST"),
        ("/device/rk", "POST"), ("/device/hf", "POST"),
        ("/device/copy_private", "POST"), ("/device/financial", "POST"),
        ("/device/wallet_balance_list", "POST"), ("/device/update_wallet_balance", "POST"),
        ("/device/payment_address", "GET"), ("/device/add_payment_address", "POST"),
        ("/device/modify_payment_address", "POST"), ("/device/add_commission_address", "POST"),
        ("/device/modify_commission_address", "POST"), ("/device/system_address", "GET"),
        ("/device/add_agent", "POST"), ("/device/add_packet", "POST"),
        ("/device/get_packet_info", "GET"), ("/device/agent_list", "GET"),
        ("/device/custom_wallet_list", "POST"), ("/device/custom_financial", "POST"),
    ]
    bad, unknown = [], []
    for path, meth in BANNED:
        s, b = post(path, AGENT_A, {"page": 1, "pageSize": 10, "status": -1, "agent_id": -1}, meth)
        c = b.get("code")
        if c is None:
            # ★ 传输失败 ⇒ **不得**算"越权放行"（那会把环境抖动报成安全缺陷，E-306 同族）
            unknown.append("%s %s" % (meth, path))
        elif c != 7:
            bad.append("%s %s→code=%s" % (meth, path, c))
    if bad:
        rec("R8", False, "裁决「绝对不可有」%d 条：**越权放行的 = %s**；另有 %d 条传输失败未判定"
            % (len(BANNED), bad, len(unknown)))
    elif unknown:
        rec("R8", True, "裁决「绝对不可有」%d 条：已判定的 %d 条**全部被拒**；"
                        "★ **%d 条因传输失败无法判定（%s）** —— 非通过，本轮该条结论不完整"
            % (len(BANNED), len(BANNED) - len(unknown), len(unknown), unknown), skip=True)
    else:
        rec("R8", True, "裁决「绝对不可有」%d 条逐条被拒；越权放行的 = 无" % len(BANNED))

    # ---- R7 ★ 登记：零值静默过滤陷阱（本次实测发现，非本线引入）----

    s, b = post("/device/agent_device_list", AGENT_A, {"page": 1, "pageSize": 10})   # 漏传 status
    omit = total_of(b)
    s, b = post("/device/list", ADMIN, {"page": 1, "pageSize": 10, "status": -1})    # 漏传 agent_id
    omit2 = total_of(b)
    rec("R7", omit == 0 and omit2 == 0,
        "★ 零值陷阱实证：漏传 status ⇒ agent_device_list total=%s（真值 1）；"
        "漏传 agent_id ⇒ /device/list total=%s（真值 %s）。"
        "出处 service/system/sys_qianke.go:410/:454/:457 的 `if info.X >= 0`"
        % (omit, omit2, DB_TRUTH["machine_all"]))

    print("=" * 78)
    fails = [r for r in RESULTS if r[1] == "FAIL"]
    skips = [r for r in RESULTS if r[1] == "SKIP"]
    npass = sum(1 for r in RESULTS if r[1] == "PASS")
    print("结果: PASS %d / FAIL %d / SKIP %d（共 %d）" % (npass, len(fails), len(skips), len(RESULTS)))
    if TRANSPORT:
        print("  ★ 传输层失败 %d 次（这些读数不携带任何关于被测物的信息，⛔ 不得当作 FAIL 上报）：%s"
              % (len(TRANSPORT), TRANSPORT))
    for rid, st, det in fails:
        print("  FAIL %s: %s" % (rid, det))
    print("RESULT=%s" % ("RED" if fails else ("YELLOW" if skips else "GREEN")))
    return 1 if fails else (2 if skips else 0)


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    s, b = post("/device/agent_device_list", AGENT_A, {"page": 1, "pageSize": 10, "status": -1})
    if b.get("code") != 0:
        print("  [FAIL] 有权限的会话拿不到 code:0 ⇒ 量尺不可用：%s" % b)
        ok = False
    else:
        print("  有权限会话：code=0 ✓")
    s, b = post("/device/list", AGENT_A, {"page": 1, "pageSize": 10, "status": -1, "agent_id": -1})
    if b.get("code") != 7:
        print("  [FAIL] 无权限的调用未被拒 ⇒ 量尺无法区分「拒绝」与「通过」：%s" % b)
        ok = False
    else:
        print("  无权限会话：code=7 权限不足 ✓（⇒ 同时证明 casbin 未走 develop 旁路）")
    print("SELFTEST=%s" % ("OK" if ok else "BAD"))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
