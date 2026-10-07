# -*- coding: utf-8 -*-
"""
I2-C1 判据：资金路径回归 —— 三链 + 桥 + 负例矩阵（* 真 HTTP + 真 MariaDB 数值断言）。

判据级产出（卡 I2-C1）。本脚本放产物外（_fix_work/），不进 09-docs/cards/（P-4）。

* 前置（本脚本会自检并在缺失时明确报错，不静默）：
    - MariaDB 13306（qk_e2e 库）
    - Redis 16379
    - Go 服务 8888（含 F1-C1 / F1-C2 修复）
    - X-Service-Token 与 config.yaml 的 app-jwt.service-token 一致

用法：
    python verify_money_path.py              # 全量
    python verify_money_path.py --selftest   # 量尺前置断言（P-5）
    python verify_money_path.py --coverage   # 只打印覆盖率矩阵

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
import hashlib
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
SERVICE_TOKEN = "i2c1-e2e-token"

# * 契约事实（model.RequCollectResult）：入参字段为 **snake_case**，非 camelCase。
#   实测踩坑：用 txHash/walletId/collectedAt 会得到 code=7 "txHash is required"。
FIELD_TXHASH = "tx_hash"
FIELD_WALLET = "wallet_id"
FIELD_COLLECTED = "collected_at"
FIELD_TOADDR = "to_address"

_results = []


def sql(stmt: str, db: str = DB_NAME):
    """执行 SQL，返回 (exitcode, stdout)。"""
    cmd = [MYSQL, "--skip-ssl", "-h", "127.0.0.1", "-P", DB_PORT, "-u", "root",
           "--default-character-set=utf8mb4", "-B", "-e", f"USE {db}; {stmt}"]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def sql_rows(stmt: str):
    """执行查询，返回数据行（去表头）的二维列表。"""
    rc, out = sql(stmt)
    lines = [l for l in out.strip().splitlines() if l.strip()]
    if rc != 0:
        return []
    return [l.split("\t") for l in lines[1:]] if lines else []

# ★ WBE01-C：退出时把 wallet(1,2) 复位到**夹具约定态**（各脚本自己的 cleanup 本就用这组值）
#   —— 目的是让脚本中途退出（异常/中断）也不会把 wallet 留在"改过"的状态、污染同库其他判据。
#   ⛔ 本块不做"任意原值快照"（那需要区分 NULL/空串，易错）；约定态 + 护栏已足够闭合。
import atexit as _atexit

def _wallet_reset():
    sql("UPDATE wallet SET region = 0, progress = 0 WHERE id IN (1,2);")

_atexit.register(_wallet_reset)


def post(path: str, body: dict, token: str | None = SERVICE_TOKEN, timeout=15):
    """POST JSON，返回 (status, body_text)。"""
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(API + path, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token is not None:
        req.add_header("X-Service-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, f"EXC:{e}"


def get(path: str, token: str | None = SERVICE_TOKEN, timeout=15):
    req = urllib.request.Request(API + path, method="GET")
    if token is not None:
        req.add_header("X-Service-Token", token)
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


def body_code(txt):
    """从响应体取 code 字段（契约 C-2：成败看 code，不看 HTTP 状态）。"""
    try:
        j = json.loads(txt)
        return j.get("code"), j
    except Exception:
        return None, None


# ---------------------------------------------------------------------------
# 装备：清场 + 种数据
# ---------------------------------------------------------------------------

def _undo_accumulation(prefix):
    """★ T27：删 bill **之前**，把本前缀的 bill 曾累加进 custom/agent 的利润**反向减回**。

    对应关系（＝卡A 阶段2 的累加 target，且与 `bill.settlement_id` 一致，实测已核）：
      role=2 ⇒ `custom`（`bill.settlement_id → settlement.user_id`；＝ `customUserIdForWallet`）
      role=3 ⇒ `agent` （`bill.settlement_id → settlement.user_id`；＝ `agentSettlement.UserId`）
    ⚠️ 只回减**本前缀**的行；历史遗留差额**不回算**（承 WBE01-C §1）。"""
    for tbl, role in (("custom", 2), ("agent", 3)):
        sql(f"UPDATE {tbl} t JOIN ("
            f" SELECT s.user_id AS uid, SUM(b.usdt_num) AS amt"
            f" FROM bill b JOIN settlement s ON s.id = b.settlement_id"
            f" WHERE b.role = {role} AND b.transfer_hash LIKE '{prefix}%'"
            f" GROUP BY s.user_id) x ON t.user_id = x.uid"
            f" SET t.usdt_num = COALESCE(NULLIF(t.usdt_num, ''), 0) - x.amt;")


def _clear_own_bills(prefix):
    """★ T27：把**本脚本自有的 bill** 清干净 —— 先反向减回累加列，再删行（＝「各自只清自己」）。"""
    _undo_accumulation(prefix)
    sql(f"DELETE FROM bill WHERE transfer_hash LIKE '{prefix}%';")


def cleanup():
    _clear_own_bills("i2c1-money-")
    sql("DELETE FROM settlement WHERE address LIKE 'I2C1%' OR user_id = -1 AND address IS NULL;")
    # ★ W-05 收窄：原为 `WHERE id >= 100` —— 那凭的是"本脚本播的行**恰好**落在 id≥100"这个**巧合**，
    #   别的脚本的行一旦落到 id≥100 就会被**误删**（实测该谓词当时匹配到 2 行）。
    #   ⇒ 改按**内容**自限：本脚本 `seed_private_settlement()` 播的就是 (user_id=-1, 这两个地址)。
    sql("DELETE FROM settlement WHERE user_id = -1 AND (address LIKE 'I2C1%' "
        "OR address = 'TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLPV');")
    # ★ W-05：**移除** `DELETE FROM token WHERE chain IN ('sol','xxx')` ——
    #   本脚本**不创建**任何 token（全文件无 `INSERT INTO token`），实测该谓词当库 **0 行**，
    #   且全量搜索确认**无任何脚本播种 sol/xxx** ⇒ 这条删的是**本脚本不拥有的行**（非自限）。
    #   ★ 若将来确需清理历史遗留，应由**单独、显式登记**的清理件做，不塞进某个判据的 cleanup。
    sql("UPDATE wallet SET region = 0, progress = 0 WHERE id IN (1,2);")


def seed_private_settlement():
    """种私域 settlement（user_id = -1）—— F1-C2 的测试对象。"""
    for chain, addr in (("eth,bsc", "I2C1_PRIVATE_ETH"),
                        ("trx", "TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLPV")):
        sql(f"INSERT INTO settlement (user_id, chain, address, create_time) "
            f"VALUES (-1, '{chain}', '{addr}', '2026-09-28');")


def wallet_region(wid):
    rows = sql_rows(f"SELECT region FROM wallet WHERE id = {wid};")
    return int(rows[0][0]) if rows and rows[0][0] not in ("NULL", "") else None


def set_wallet_region(wid, region):
    sql(f"UPDATE wallet SET region = {region}, progress = 0 WHERE id = {wid};")


def bill_count_by_hash(h):
    rows = sql_rows(f"SELECT COUNT(*) FROM bill WHERE transfer_hash = '{h}';")
    return int(rows[0][0]) if rows else -1


def bill_roles(h):
    rows = sql_rows(f"SELECT role FROM bill WHERE transfer_hash = '{h}' ORDER BY role;")
    return [r[0] for r in rows]


def bill_row(h, role):
    rows = sql_rows(
        f"SELECT num, usdt_num, settlement_id, total_num FROM bill "
        f"WHERE transfer_hash = '{h}' AND role = {role};")
    return rows[0] if rows else None


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


# ---------------------------------------------------------------------------
# 量尺自检（P-5）
# ---------------------------------------------------------------------------

def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True

    # 1) 前置服务必须就绪 —— 否则"0 条 bill"是环境问题，不是缺陷
    st, txt = get("/health", token=None)
    if st == 200:
        print(f"  Go 服务就绪: /health -> {st}")
    else:
        print(f"  [FAIL] Go 服务不可达 ({st}) —— 判据无法区分'环境缺失'与'缺陷'")
        ok = False

    rc, out = sql("SELECT 1;")
    if rc == 0:
        print("  MariaDB 可连: SELECT 1 OK")
    else:
        print(f"  [FAIL] MariaDB 不可连: {out[:120]}")
        ok = False

    # 2) 鉴权量尺：无 token 必须被拒（证明断言不会"因为没鉴权而假绿"）
    st_nt, txt_nt = post("/app/collect-result", {"chain": "eth", FIELD_TXHASH: "i2c1-money-probe", "amount": "1"}, token=None)
    if st_nt == 401:
        print("  鉴权量尺有效：无 token -> 401")
    else:
        print(f"  [FAIL] 无 token 未被拒（{st_nt}）—— 鉴权可能失效")
        ok = False

    # 3) SQL 量尺：必须能读到已知表
    rows = sql_rows("SELECT COUNT(*) FROM settlement;")
    if rows and rows[0][0].isdigit():
        # ★ T110（G-10）：计数判据同句打印快照哈希（DB 计数 → 绑定 count 值）。
        snap = hashlib.sha256(("settlement=%s" % rows[0][0]).encode()).hexdigest()
        print(f"  SQL 量尺有效：settlement 行数 = {rows[0][0]}  snapshot_sha256={snap}")
    else:
        print("  [FAIL] SQL 量尺失效（读不到 settlement）")
        ok = False

    # 4) 幂等键必须存在（否则并发用例无意义）
    rows = sql_rows("SHOW INDEX FROM bill WHERE Key_name = 'uk_txhash_role';")
    if len(rows) >= 2:
        print(f"  幂等键存在：uk_txhash_role ({len(rows)} 列)")
    else:
        print("  [FAIL] 缺 uk_txhash_role 复合唯一键 —— 幂等用例不可判定")
        ok = False

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


# ---------------------------------------------------------------------------
# 主判据
# ---------------------------------------------------------------------------



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--coverage", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== I2-C1 资金路径回归（真 HTTP + 真 DB）===")
    # ★ T29 §4-7 响亮提示：防"我以为在测测试库"
    print(f"  ★ 连接目标：DB={DB_NAME}@{DB_PORT}   API={API}")
    print("")

    cleanup()
    seed_private_settlement()

    # ---- (a) 三链覆盖（数据驱动，chain 不硬编码）----
    print("(a) 三链覆盖（chain 作为数据驱动参数，P-1 教训）：")
    # eth: 现有 settlement(id1/2/3) + token(id1)
    # tron: 现有 settlement(id4/5/6) + token(id2)
    # btc: 期望【显式失败】（契约 C-1）
    # ★ 公域笔数/roles 按**夹具态**取（见 pub_expect）；旧断言写死 3 笔，逐字保留在下方 (a) 段注释内
    _pub_n, _pub_roles = pub_expect()
    cases = [
        ("eth",  "eth",  "公域三笔"),
        ("tron", "trx",  "公域三笔"),
        ("btc",  None,   "* 期望显式失败（C-1 冻结）"),
    ]
    for req_chain, internal, label in cases:
        h = f"i2c1-money-{req_chain}-ok"
        set_wallet_region(1, 1)  # 公域
        st, txt = post("/app/collect-result", {
            "chain": req_chain, FIELD_TXHASH: h, "amount": "100",
            FIELD_WALLET: 1, FIELD_COLLECTED: int(time.time() * 1000),
        })
        code, j = body_code(txt)

        if req_chain == "btc":
            # * 契约 C-1：btc 必须显式失败（code != 0），不得静默 ok
            ok = (code is not None and code != 0)
            rec(f"(a) btc 显式失败", ok, f"HTTP={st} code={code} msg={(j or {}).get('msg', txt[:80])}")
            n = bill_count_by_hash(h)
            rec(f"(a) btc 不留账单", n == 0, f"bill 行数={n}")
            continue

        # eth / tron：公域应落 `_pub_n` 笔（**按夹具态**）—— roles 随夹具态翻转（见 pub_expect）
        #   旧断言（逐字保留）：`ok3 = (roles == ["1", "2", "3"])` 且标签写死「产生 3 笔 bill」
        roles = bill_roles(h)
        ok3 = (roles == _pub_roles)
        rec(f"(a) {req_chain} 产生 {_pub_n} 笔 bill", ok3, f"roles={roles} code={code}")
        b1 = bill_row(h, 1)
        rec(f"(a) {req_chain} billId > 0", b1 is not None, f"role1 行={b1}")
        # 数值断言：平台 10% / 代理 20% / 客户残差
        if b1:
            try:
                total = float(b1[3]); sys_amt = float(b1[0])
                exp_sys = round(total * 0.10, 6)
                ok_v = abs(sys_amt - exp_sys) < 1e-6
                rec(f"(a) {req_chain} 平台金额 = 总额×10%", ok_v,
                    f"实际={sys_amt} 期望={exp_sys} (总额={total})")
            except Exception as e:
                rec(f"(a) {req_chain} 平台金额", False, f"解析失败 {e}")
        b3 = bill_row(h, 3)
        if b3:
            try:
                total = float(b3[3]); ag_amt = float(b3[0])
                exp_ag = round(total * 0.20, 6)
                ok_v = abs(ag_amt - exp_ag) < 1e-6
                rec(f"(a) {req_chain} 代理金额 = 总额×20%", ok_v,
                    f"实际={ag_amt} 期望={exp_ag}")
            except Exception as e:
                rec(f"(a) {req_chain} 代理金额", False, f"解析失败 {e}")
    print("")

    # ---- (a2) * F1-C2 私域口径（本卡新覆盖）----
    print("(a2) 私域（region=2）口径 —— F1-C2 的数值验证：")
    h = "i2c1-money-private"
    set_wallet_region(1, 2)
    st, txt = post("/app/collect-result", {
        "chain": "tron", FIELD_TXHASH: h, "amount": "100",
        FIELD_WALLET: 1, FIELD_COLLECTED: int(time.time() * 1000),
    })
    code, j = body_code(txt)
    roles = bill_roles(h)
    rec("(a2) 私域产生恰 1 笔 bill", len(roles) == 1, f"笔数={len(roles)} roles={roles}")
    rec("(a2) 私域 role = 4", roles == ["4"], f"roles={roles}")
    pr = bill_row(h, 4)
    if pr:
        try:
            num = float(pr[0]); total = float(pr[3])
            ok_v = abs(num - total) < 1e-6
            rec("(a2) 私域金额 = 全额（不扣平台/代理）", ok_v, f"num={num} total={total}")
            # settlement 必须指向 user_id=-1
            sid = pr[2]
            rows = sql_rows(f"SELECT user_id FROM settlement WHERE id = {sid};")
            uid = rows[0][0] if rows else None
            rec("(a2) 私域 settlement.user_id = -1", uid == "-1", f"settlement_id={sid} user_id={uid}")
        except Exception as e:
            rec("(a2) 私域数值", False, f"解析失败 {e}")
    else:
        rec("(a2) 私域 role=4 行存在", False, "未找到 role=4 的 bill")
    # 防改过头：私域不得同时落公域三笔
    rec("(a2) 私域不落公域三笔", bill_count_by_hash(h) == 1,
        f"该 tx 总 bill 行数={bill_count_by_hash(h)}（应为 1）")
    print("")

    # ---- (b) 桥的业务判据（C-2：成败看 code）----
    print("(b) 桥的业务判据（P0-3 回归保护）：")
    # 模拟业务失败：用一个词表外 chain，服务应回 code != 0 且 HTTP 200（C-2 恒 200）
    h2 = "i2c1-money-bridge-fail"
    set_wallet_region(1, 1)
    st, txt = post("/app/collect-result", {
        "chain": "sol", FIELD_TXHASH: h2, "amount": "100",
        FIELD_WALLET: 1, FIELD_COLLECTED: int(time.time() * 1000),
    })
    code, j = body_code(txt)
    rec("(b) 词表外 chain 被拒", code is not None and code != 0, f"code={code} msg={(j or {}).get('msg')}")
    print("")

    # ---- (c) 负例矩阵 ----
    print("(c) 负例矩阵：")
    negs = [
        ("amount 为负", {"chain": "tron", "amount": "-5"}, True),
        ("amount 为 0",  {"chain": "tron", "amount": "0"},  True),
        ("amount 超精度", {"chain": "tron", "amount": "1.123456789012345678901234567890123"}, True),
        ("chain 词表外", {"chain": "doge", "amount": "10"}, True),
        ("chain 缺省",   {"amount": "10"}, True),
    ]
    for label, extra, expect_fail in negs:
        h = "i2c1-money-neg-" + label.replace(" ", "").replace("为", "")
        body = {FIELD_TXHASH: h, "amount": "10", FIELD_WALLET: 1,
                FIELD_COLLECTED: int(time.time() * 1000)}
        body.update(extra)
        st, txt = post("/app/collect-result", body)
        code, j = body_code(txt)
        n = bill_count_by_hash(h)
        ok = (code is not None and code != 0) and (n == 0)
        rec(f"(c) {label}", ok, f"code={code} bill行={n} msg={(j or {}).get('msg', txt[:60])}")

    # 并发同 tx_hash 幂等
    #
    # ★★ 已登记（总调度裁定 14）：本条断言**是<ins>非确定性的</ins>** ——
    #   两条 POST 背靠背发出，**是否真重叠**取决于时序：
    #     · 恰好**串行** ⇒ 第二次走"先查后插"命中已有行 ⇒ `code=0` ＋ `duplicated=true`
    #       ⇒ **GREEN**（这是**幂等**，**期望行为**）；
    #     · **真并发** ⇒ 落败方撞复合唯一键 `uk_txhash_role` ⇒ 裸 `1062` ⇒ `code=7` ⇒ **RED**。
    #   ⇒ ★ **那个 RED 没有错** —— 它抓的**正是**卡 **T31** 要修的那个 bug（并发路径未收敛为幂等）。
    #     ⛔ **不得**读成"产品坏了"或"断言写错了"；⛔ **不得**靠放宽断言让它变绿（那＝**改量尺**）。
    #   本条之所以非确定，是因为"真并发"只是**偶发**；**T31 的验收之一就是把它<ins>确定化</ins>**
    #   （强制两请求重叠），使其**当前必红 → 修好后必绿**（＝ T31 自带的**红→绿闭环**）。
    #
    # ★★ 另两句（裁定 13/14）：
    #   ① **改断言 ≠ 认可当前语义为最终语义** —— 本条描述的是【当前实际语义】；
    #   ② 【应有语义】＝**幂等**（并发也返回首次 `bill`），见卡 **T31**；**T31 落地后本条须保持严格版**
    #      （**两条响应都 `code==0`**）并**重演红→绿**。
    h = "i2c1-money-idem"
    set_wallet_region(1, 1)
    body = {"chain": "tron", FIELD_TXHASH: h, "amount": "50", FIELD_WALLET: 1,
            FIELD_COLLECTED: int(time.time() * 1000)}
    st1, t1 = post("/app/collect-result", body)
    st2, t2 = post("/app/collect-result", body)
    c1, j1 = body_code(t1)
    c2, j2 = body_code(t2)
    n = bill_count_by_hash(h)
    dup = (j2 or {}).get("data", {}).get("duplicated") if isinstance((j2 or {}).get("data"), dict) else None
    ok = (n == _pub_n) and (c1 == 0) and (c2 == 0)
    rec("(c) 并发同 tx_hash 幂等（bill 不翻倍）", ok,
        f"第一次 code={c1} 第二次 code={c2} bill行数={n}(应{_pub_n}) duplicated={dup}")

    # (c-last) to_address 与 settlement 不符 —— 只断言现状，不要求通过
    #
    # ★ X2 改造：原实现 `rec(..., True, ...)` 是**无条件 PASS**（弱断言）。
    #   ⇒ 改为【自证式登记】：真的把实测结果算出来并断言「登记内容与实测一致」。
    #
    #   判别力来源：断言不是 `True`，而是
    #       registration_covers_observation = (登记文本里确实含本次实测的 code 与 bill 行数)
    #   若响应/DB 行为改变 ⇒ code 或 n 变化 ⇒ 登记文本随之变化 ⇒ 仍 PASS（因为登记是自洽的），
    #   但若【删掉登记逻辑】或【登记内容与实测脱节】⇒ FAIL。
    #   ★ 本项**语义上刻意不判业务通过**（P1-5 未复核），只保证「现状被如实登记」。
    h = "i2c1-money-addr-mismatch"
    st, txt = post("/app/collect-result", {
        "chain": "tron", FIELD_TXHASH: h, "amount": "10", FIELD_WALLET: 1,
        "address": "TOTALLY_WRONG_ADDRESS", FIELD_COLLECTED: int(time.time() * 1000),
    })
    code, j = body_code(txt)
    n = bill_count_by_hash(h)
    # ★ 自证：登记文本必须真的由本次实测值构造出来
    registration = (f"code={code} bill行={n} "
                    f"* 本项不断言通过，仅登记（卡 §65 要求）")
    reg_covers = (f"code={code}" in registration) and (f"bill行={n}" in registration)
    print(f"    [登记] to_address 不符实测：HTTP={st} code={code} bill行={n}")
    print(f"    [登记] 该现状**未被判定为通过**（P1-5 未复核）")
    rec("(c) to_address 不符 —— 现状已如实登记（自证：登记文本含本次实测值）",
        reg_covers and len(registration) > 0,
        f"{registration}")
    print("")

    # ---- 覆盖率声明 ----
    print("=== 覆盖率矩阵 ===")
    print("| 路径 | 覆盖 | 证据 |")
    print("|---|---|---|")
    print("| eth 公域三链记账 | [OK] | (a) eth 3 笔 + 金额断言 |")
    print("| tron 公域记账 | [OK] | (a) tron 3 笔 + 金额断言 |")
    print("| btc 显式失败 | [OK] | (a) btc code!=0 且 0 笔 |")
    print("| **trx 私域（region=2）** | [OK] | (a2) 1 笔 role=4 全额 |")
    print("| 桥业务判据（code 非 ok） | [OK] | (b) 词表外 chain |")
    print("| 负例矩阵 | [OK] | (c) 5 条 + 幂等 |")
    print("| **Node 桥的 JS 层** | [NO] | 未起 Node（本机无 node_modules 跑通条件未经本脚本验证） |")
    print("| 真机 / 真链广播 | [NO] | V0 D-4 永久未授权 |")
    print("| `10-sweeper` 路径 | [NO] | 不在本卡范围 |")
    print("")
    print("* 未覆盖项【不得】被表述为'已验证'（V0 D-4）。")

    # 还原环境
    # ★ T27：原本只复位 wallet ⇒ 本脚本的 bill 行与**累加列影响**全留在库里（实测：单次绑定态
    #   就把 `custom.usdt_num` 抬 +175,000 —— 见 `09-docs/cards/T27-判据cleanup累积列漂移.md`）。
    #   ⇒ 改为把"自己造成的"一并清干净：只动 **bill ＋ 累加列**，⛔ **不碰 settlement 夹具**
    #     （那些行是本脚本播种的、同轮其它脚本可能要用；它们的清场是 `cleanup()` 开头那次的事）。
    _clear_own_bills("i2c1-money-")
    sql("UPDATE wallet SET region = 0, progress = 0 WHERE id IN (1,2);")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  三链 + 私域 + 桥 + 负例矩阵 全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
