# -*- coding: utf-8 -*-
"""
F1-C8 判据：负金额/零金额必须被显式拒绝，且不落账。

判据先于实现（判据 9）。本脚本放产物外（_fix_work/），不进 09-docs/cards/（P-4）。

★ 真 HTTP + 真 DB 数值断言（非静态）。
★ 前置：MariaDB 13306 / Redis 16379 / Go 8888（含 F1-C2 修复）。

用法：
    python verify_f1c8_amount_guard.py              # 全量
    python verify_f1c8_amount_guard.py --selftest   # 量尺前置断言（P-5）

退出码：0 = 全绿；非 0 = 有红。
"""
from __future__ import annotations

# ★ X3：本脚本【自带】UTF-8 输出，不依赖调用方设置 PYTHONIOENCODING（P-10）
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
import sys as _sys

_os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # 旧版 Python 无 reconfigure 时静默降级
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

MD_BIN = IOS_ROOT + r"\_integration\_fix_work\_toolchain\mariadb-11.4.4-winx64\bin"
MYSQL = os.path.join(MD_BIN, "mysql.exe")
DB_PORT = "13306"
# ★ T29（WBE01-D · (乙-1) 隔离）：**可注入** —— 默认值**逐字等于现状**；不设环境变量则行为逐字不变。
DB_NAME = os.environ.get("DSH_DB", "qk_e2e")
API = os.environ.get("DSH_API", "http://127.0.0.1:8888")
assert DB_NAME == "qk_e2e_test", "⛔ 拒绝裸跑：只允许隔离库 qk_e2e_test（须经 iso_run.py 注入）"
assert API == "http://127.0.0.1:8900", "⛔ 拒绝裸跑：只允许隔离实例 8900（须经 iso_run.py 注入）"
TOKEN = "i2c1-e2e-token"

_results = []


def sql(stmt):
    cmd = [MYSQL, "--skip-ssl", "-h", "127.0.0.1", "-P", DB_PORT, "-u", "root",
           "--default-character-set=utf8mb4", "-B", "-e", f"USE {DB_NAME}; {stmt}"]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def sql_rows(stmt):
    rc, out = sql(stmt)
    if rc != 0:
        return []
    lines = [l for l in out.strip().splitlines() if l.strip()]
    return [l.split("\t") for l in lines[1:]] if lines else []

# ★ WBE01-C：退出时把 wallet(1,2) 复位到**夹具约定态**（各脚本自己的 cleanup 本就用这组值）
#   —— 目的是让脚本中途退出（异常/中断）也不会把 wallet 留在"改过"的状态、污染同库其他判据。
#   ⛔ 本块不做"任意原值快照"（那需要区分 NULL/空串，易错）；约定态 + 护栏已足够闭合。
import atexit as _atexit

def _wallet_reset():
    sql("UPDATE wallet SET region = 0, progress = 0 WHERE id IN (1,2);")

_atexit.register(_wallet_reset)


def post(path, body, timeout=15):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(API + path, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Service-Token", TOKEN)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, f"EXC:{e}"


def rec(name, ok, detail):
    _results.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def code_of(txt):
    try:
        return json.loads(txt).get("code")
    except Exception:
        return None


def bill_count(h):
    rows = sql_rows(f"SELECT COUNT(*) FROM bill WHERE transfer_hash = '{h}';")
    return int(rows[0][0]) if rows else -1


def _undo_accumulation(prefix):
    """★ T27：删 bill **之前**，把本前缀的 bill 曾累加进 custom/agent 的利润**反向减回**。
    对应关系见 `verify_f1c9_toaddress_guard.py` 同名函数（role=2 ⇒ custom / role=3 ⇒ agent，
    均按 `bill.settlement_id → settlement.user_id`）。⚠️ 历史遗留差额**不回算**（承 WBE01-C §1）。"""
    for tbl, role in (("custom", 2), ("agent", 3)):
        sql(f"UPDATE {tbl} t JOIN ("
            f" SELECT s.user_id AS uid, SUM(b.usdt_num) AS amt"
            f" FROM bill b JOIN settlement s ON s.id = b.settlement_id"
            f" WHERE b.role = {role} AND b.transfer_hash LIKE '{prefix}%'"
            f" GROUP BY s.user_id) x ON t.user_id = x.uid"
            f" SET t.usdt_num = COALESCE(NULLIF(t.usdt_num, ''), 0) - x.amt;")


def cleanup():
    _undo_accumulation("i2c1-f1c8-")
    sql("DELETE FROM bill WHERE transfer_hash LIKE 'i2c1-f1c8-%';")
    sql("UPDATE wallet SET region = 0, progress = 0 WHERE id IN (1,2);")


# ★★ WBE01-A 阶段2「单态断言」修复（与 `verify_f1c9_toaddress_guard.py` **同源同法** ·
#   总调度接班人 ⌛2026-10-03 裁定）。原断言写死「公域 3 笔（role 1/2/3）」，
#   隐含「夹具已绑定客户」；夹具解绑/复位后会同型误红。
#   改法：运行时读夹具态（packet.custom_user_id），按态取期望。旧断言逐字保留在用法处注释块内。
def fixture_bound():
    """夹具态：`packet` 里是否存在**已绑定客户**的包（custom_user_id <> 0）。"""
    rows = sql_rows("SELECT COUNT(*) FROM packet WHERE custom_user_id <> 0;")
    return bool(rows and rows[0][0].isdigit() and int(rows[0][0]) > 0)


def pub_expect(bound=None):
    """公域收款期望 `(笔数, roles)`：绑定 ⇒ 客户支可解 ⇒ 3 笔；未绑定 ⇒ 不可解 ⇒ 2 笔。"""
    if bound is None:
        bound = fixture_bound()
    return (3, ["1", "2", "3"]) if bound else (2, ["1", "3"])


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True

    # 1) 服务就绪
    try:
        req = urllib.request.Request(API + "/health")
        with urllib.request.urlopen(req, timeout=5) as r:
            if r.status == 200:
                print("  Go 服务就绪: /health 200")
            else:
                print(f"  [FAIL] /health -> {r.status}")
                ok = False
    except Exception as e:
        print(f"  [FAIL] Go 服务不可达: {e}")
        ok = False

    # 2) DB 就绪
    rows = sql_rows("SELECT COUNT(*) FROM bill;")
    if rows and rows[0][0].isdigit():
        print(f"  MariaDB 就绪: bill 表可读（现 {rows[0][0]} 行）")
    else:
        print("  [FAIL] MariaDB 不可读")
        ok = False

    # 3) ★ 量尺有效性：必须能观察到一个【正值】请求成功落账
    #    否则"没落账"可能因为环境坏了，而不是因为被拒绝（P-5 精神）
    #    ★ 笔数按**夹具态**取（见 pub_expect）；旧断言写死 3 笔
    _pub_n, _ = pub_expect()
    cleanup()
    h = "i2c1-f1c8-selftest-pos"
    st, txt = post("/app/collect-result", {
        "chain": "tron", "tx_hash": h, "amount": "100",
        "wallet_id": 1, "collected_at": int(time.time() * 1000),
    })
    c = code_of(txt)
    n = bill_count(h)
    if c == 0 and n == _pub_n:
        print(f"  量尺有效：正值请求 code=0 且落 {_pub_n} 笔（证明写入通道可用）")
    else:
        print(f"  [FAIL] 正值请求未正常落账 (code={c}, bill={n}, 应={_pub_n}) —— 量尺无法区分'被拒绝'与'环境坏'")
        ok = False

    # 4) 量尺有效性：SQL 计数要能区分 0 与 3
    n0 = bill_count("i2c1-nonexistent-xyz")
    if n0 == 0:
        print("  计数有效：不存在的 tx -> 0 笔")
    else:
        print(f"  [FAIL] 计数异常: 不存在 tx -> {n0}")
        ok = False

    cleanup()
    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== F1-C8 负/零金额校验（真 HTTP + 真 DB）===")
    # ★ T29 §4-7 响亮提示：防"我以为在测测试库"
    print(f"  ★ 连接目标：DB={DB_NAME}@{DB_PORT}   API={API}")
    cleanup()

    ts = int(time.time() * 1000)
    # ★ 正例笔数按**夹具态**取（见 pub_expect）；旧断言把 R4 写死「3」
    _pub_n, _pub_roles = pub_expect()
    cases = [
        # (标签, amount, region, 期望 code!=0, 期望笔数)
        ("R1 amount = -5",          "-5",        0, True,  0),
        ("R2 amount = 0",           "0",         0, True,  0),
        ("R3 amount = -0.000001",   "-0.000001", 0, True,  0),
        # 旧断言（逐字保留）：("R4 amount = 100 (正例, 防改过头)", "100", 0, False, 3),
        ("R4 amount = 100 (正例, 防改过头)", "100", 0, False, _pub_n),
        ("R5 私域 amount = -5",     "-5",        2, True,  0),
    ]

    for label, amt, region, expect_fail, expect_bills in cases:
        sql(f"UPDATE wallet SET region = {region}, progress = 0 WHERE id = 1;")
        h = "i2c1-f1c8-" + label.split()[0]
        st, txt = post("/app/collect-result", {
            "chain": "tron", "tx_hash": h, "amount": amt,
            "wallet_id": 1, "collected_at": ts,
        })
        c = code_of(txt)
        n = bill_count(h)
        if expect_fail:
            ok = (c is not None and c != 0) and (n == 0)
            rec(label, ok, f"code={c} bill={n}(应0) HTTP={st} msg={txt[:90]}")
        else:
            ok = (c == 0) and (n == expect_bills)
            rec(label, ok, f"code={c} bill={n}(应{expect_bills}) HTTP={st}")

    # 附加：确证负金额不再产生负数账单
    h = "i2c1-f1c8-R1"
    rows = sql_rows(f"SELECT role, num FROM bill WHERE transfer_hash = '{h}';")
    rec("附加：负金额无任何 bill 行", len(rows) == 0, f"行数={len(rows)} {rows}")

    cleanup()
    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  负/零金额全部被拒、正例不受影响")
    return 0


if __name__ == "__main__":
    sys.exit(main())
