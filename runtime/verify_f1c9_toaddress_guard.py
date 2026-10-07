# -*- coding: utf-8 -*-
"""
F1-C9 判据：to_address 必须与本次记账涉及的 settlement 地址之一一致。

判据先于实现（判据 9）。本脚本放产物外（_fix_work/），不进 09-docs/cards/（P-4）。

★ 判定规则（依据 scan.go 实读，见卡 F1-C9 规格 (a)）：
    - 私域（Region==2）: 记账涉及 {privateSettlement.address}（user_id=-1）
    - 公域（Region!=2）: 记账涉及 {systemSettlement, 客户 settlement, 代理 settlement}
    - to_address 为空 => 不校验（向后兼容）
    - to_address 非空且不在集合内 => 拒绝

★ 真 HTTP + 真 DB 数值断言。
★ 前置：MariaDB 13306 / Redis 16379 / Go 8888。

用法：
    python verify_f1c9_toaddress_guard.py                  # 全量
    python verify_f1c9_toaddress_guard.py --selftest       # 量尺前置断言（P-5）
    python verify_f1c9_toaddress_guard.py --selftest-assert # 断言逻辑自检（双向可红，不落库）

★ R1/R3/R7 的期望**按运行时夹具态**（packet.custom_user_id）取，不再是常量
  （WBE01-A 阶段2 修「单态断言」；旧断言逐字保留在 main() 注释块内）。

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


def bill_roles(h):
    rows = sql_rows(f"SELECT role FROM bill WHERE transfer_hash = '{h}' ORDER BY role;")
    return [r[0] for r in rows]


def settlement_addr(sid):
    rows = sql_rows(f"SELECT address FROM settlement WHERE id = {sid};")
    return rows[0][0] if rows else None


def _undo_accumulation(prefix):
    """★ T27：删 bill **之前**，把本前缀的 bill 曾累加进 custom/agent 的利润**反向减回**。

    对应关系（＝卡A 阶段2 的累加 target，且与 `bill.settlement_id` 一致，实测已核）：
      role=2 ⇒ `custom`（`bill.settlement_id → settlement.user_id`；＝ `customUserIdForWallet`）
      role=3 ⇒ `agent` （`bill.settlement_id → settlement.user_id`；＝ `agentSettlement.UserId`）
    ⇒ 与 WBE01-C(甲)「各自只清自己」**同一精神**：把自己造成的影响清干净，而不只是清行。
    ⚠️ 只回减**本前缀**的行；历史遗留的差额**不回算**（承 WBE01-C §1）。"""
    for tbl, role in (("custom", 2), ("agent", 3)):
        sql(f"UPDATE {tbl} t JOIN ("
            f" SELECT s.user_id AS uid, SUM(b.usdt_num) AS amt"
            f" FROM bill b JOIN settlement s ON s.id = b.settlement_id"
            f" WHERE b.role = {role} AND b.transfer_hash LIKE '{prefix}%'"
            f" GROUP BY s.user_id) x ON t.user_id = x.uid"
            f" SET t.usdt_num = COALESCE(NULLIF(t.usdt_num, ''), 0) - x.amt;")


def cleanup():
    _undo_accumulation("i2c1-f1c9-")
    sql("DELETE FROM bill WHERE transfer_hash LIKE 'i2c1-f1c9-%';")
    sql("UPDATE wallet SET region = 0, progress = 0 WHERE id IN (1,2);")


def addr_set_for(region, chain_like="trx"):
    """
    按 region + chain 返回本次记账涉及的 settlement 地址集合（实测自 DB）。

    ★ 必须按 chain 过滤：服务端用 `settlement.chain LIKE '%<chain>%'` 定位，
      故 eth 组与 trx 组是【互斥】的。
      首版未按 chain 过滤，导致 R1/R4 传入 eth 地址却被 trx 请求拒绝 —— 那是
      【判据构造错误】，不是产物缺陷（实测确认校验逻辑本身是对的）。
    """
    out = []
    cl = f"%{chain_like}%"
    if region == 2:
        rows = sql_rows(
            f"SELECT address FROM settlement WHERE user_id = -1 AND chain LIKE '{cl}';")
        out = [r[0] for r in rows]
    else:
        rows = sql_rows(
            f"SELECT address FROM settlement WHERE user_id = 0 AND chain LIKE '{cl}';")
        out += [r[0] for r in rows]
        # ★★ WBE01-A 卡A：客户分支**已翻转**（不是删除）—— 旧形态逐字保留在下方注释里。
        #   为什么改：旧形态 `custom JOIN settlement ON user_id` **没有"哪个客户"的谓词**
        #     ⇒ 恒取表里全部客户（单租户铁证，见 WBE01-A 设计件 §1.2）。多租户下，
        #     客户应收地址必须**按域**解出：bill.wallet_id → wallet → machine → agent → packet.custom_user_id
        #     ⇒ 服务将只接受"该 wallet 所属 packet 的客户"的 settlement 地址。
        #   依据：总调度1 ⌛2026-10-03 裁定⑤（wallet_id 链为唯一事实源）。
        #   翻转方式：期望集合改按**域**构造；旧句保留为注释（留痕，勿删）。
        #   ★ 新断言**能独立失败**：本函数只负责构造"服务应当接受的地址集合"；
        #     若产物侧仍是单租户（会接受 custom(201) 的地址），而期望集合里已无该地址
        #     ⇒ 判据的 R1/R4 会出现「服务接受、期望不接受」⇒ 红。届时红是**真红**，不是恒红。
        #
        #   旧（本卡改动前，逐字保留备查）：
        #     rows = sql_rows(
        #         "SELECT s.address FROM custom c LEFT JOIN settlement s ON s.user_id = c.user_id "
        #         f"WHERE s.chain LIKE '{cl}';")
        #     out += [r[0] for r in rows]
        rows = sql_rows(
            "SELECT s.address FROM packet p "
            "JOIN agent a ON a.packet_id = p.id "
            "JOIN machine m ON m.agent_id = a.id "
            "JOIN wallet w ON w.machine_id = m.id "
            "JOIN bill b ON b.wallet_id = w.id "
            "JOIN settlement s ON s.id = b.settlement_id "
            f"WHERE p.custom_user_id <> 0 AND s.chain LIKE '{cl}';")
        out += [r[0] for r in rows]
        rows = sql_rows(
            "SELECT s.address FROM agent a LEFT JOIN settlement s ON s.user_id = a.user_id "
            f"WHERE s.chain LIKE '{cl}';")
        out += [r[0] for r in rows]
    return [a for a in out if a and a != "NULL"]


# ★★ WBE01-A 卡A 阶段2 · 修「单态断言」（总调度接班人 ⌛2026-10-03 裁定「发现一」）
#   问题：R1/R3 写死「应 3 笔」、R7 写死「未绑定应拒」 —— 两者对**夹具是否绑定**做了
#   相反的常量假设 ⇒ 任一夹具态下都不可能全绿（绑定态 R7 红；解绑态 R1/R3 红）。
#   实测（本线 ⌛2026-10-03 两态各跑一次）：绑定 ⇒ R1/R3 3 笔 roles[1,2,3]、R7 code=0；
#                                              解绑 ⇒ R1/R3 2 笔 roles[1,3]、R7 code=7。
#   改法：**运行时读夹具态**（packet.custom_user_id），按态取期望；
#         原断言逐字保留在 main() 的注释块里（只翻转、不删留痕）。
def fixture_bound():
    """夹具态：`packet` 里是否存在**已绑定客户**的包（custom_user_id <> 0）。"""
    rows = sql_rows("SELECT COUNT(*) FROM packet WHERE custom_user_id <> 0;")
    return bool(rows and rows[0][0].isdigit() and int(rows[0][0]) > 0)


def pub_expect(bound):
    """公域收款（R1/R3）期望：绑定 ⇒ 客户支可解 ⇒ 3 笔；未绑定 ⇒ 客户支不可解 ⇒ 2 笔。"""
    return (3, ["1", "2", "3"]) if bound else (2, ["1", "3"])


def r7_expect(bound):
    """R7（公域 + 客户地址）期望：未绑定 ⇒ 解不出客户 ⇒ 应拒；绑定 ⇒ 可解 ⇒ 应接受（同 R1 口径）。"""
    if bound:
        b, rs = pub_expect(True)
        return (False, b, rs)
    return (True, 0, [])


def judge(expect_fail, exp_bills, exp_roles, code, n, roles):
    """单一断言求值（抽出以便 `--selftest-assert` 用合成观测做「双向可红」自检）。"""
    if expect_fail:
        return ((code is not None and code != 0) and n == 0,
                f"code={code} bill={n}(应0) roles={roles}")
    return ((code == 0) and n == exp_bills and roles == exp_roles,
            f"code={code} bill={n}(应{exp_bills}) roles={roles}")


def assert_selftest():
    """★「双向可红」自检 —— 裁定「发现一」的验收：**两个方向的 FAIL 明细都要打出来**（不是只打 OK）。

    ⚠️ 本项自检为**合成观测**，非真变异；理由＝避免累积列漂移
       （本线实测：绑定态每建 1 笔 role=2 就抬 `custom.usdt_num` +70、每建 1 笔 role=3 抬 `agent.usdt_num` +20；
        本次两跑合计 +210/+100，见 `WBE01-A-阶段2-单态断言修复与红绿对照`）。"""
    print("=== 断言逻辑自检（双向可红 · 合成观测，不落库）===")
    ok = True
    for bound in (True, False):
        tag = "绑定态" if bound else "解绑态"
        b, rs = pub_expect(bound)
        ef, eb, er = r7_expect(bound)
        print(f"\n[{tag}] 期望：R1/R3 ⇒ {b} 笔 {rs}；R7 ⇒ {'拒绝' if ef else '接受'}")
        # ── 正方向：正确观测必须 PASS ──
        for nm, a in (("R1/R3", (False, b, rs, 0, b, rs)),
                      ("R7", (ef, eb, er) + ((7, 0, []) if ef else (0, eb, er)))):
            good, det = judge(*a)
            print(f"  [{'PASS' if good else 'FAIL'}] {nm} 正确观测: {det}")
            ok = ok and good
        # ── 负方向：必须 FAIL（且打出明细 —— 这是"断言能独立失败"的可机检证据）──
        for nm, a in (("R1/R3 计数被改坏", (False, b, rs, 0, (3 if b == 2 else 2), rs)),
                      ("R1/R3 被服务拒绝", (False, b, rs, 7, 0, [])),
                      ("R7 门禁被摘（取反）", (ef, eb, er) + ((0, eb, er) if ef else (7, 0, [])))):
            good, det = judge(*a)
            print(f"  [{'PASS' if good else 'FAIL'}] {nm}: {det}")
            ok = ok and (not good)
    print("\nASSERT_SELFTEST=" + ("OK" if ok else "BAD"))
    return 0 if ok else 3


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True

    try:
        req = urllib.request.Request(API + "/health")
        with urllib.request.urlopen(req, timeout=5) as r:
            print(f"  Go 服务就绪: /health {r.status}")
    except Exception as e:
        print(f"  [FAIL] Go 服务不可达: {e}")
        ok = False

    rows = sql_rows("SELECT COUNT(*) FROM settlement;")
    if rows and rows[0][0].isdigit():
        print(f"  MariaDB 就绪: settlement {rows[0][0]} 行")
    else:
        print("  [FAIL] MariaDB 不可读")
        ok = False

    # ★ 关键：地址集合必须非空，否则校验逻辑无从判定
    g = addr_set_for(0, "trx")
    p = addr_set_for(2, "trx")
    ge = addr_set_for(0, "eth")
    if g:
        print(f"  公域(trx)地址集合非空 ({len(g)} 个)")
    else:
        print("  [FAIL] 公域(trx) settlement 地址集合为空 —— 判据不可判定")
        ok = False
    if p:
        print(f"  私域(trx)地址集合非空 ({len(p)} 个)")
    else:
        print("  [FAIL] 私域(trx) settlement 地址集合为空 —— 判据不可判定")
        ok = False
    # ★ 专项：按 chain 过滤必须有效（跨链地址不得混入）
    if ge and g:
        overlap = set(ge) & set(g)
        if overlap:
            print(f"  [FAIL] eth 组与 trx 组地址有交叠 {overlap} —— 按 chain 过滤失效")
            ok = False
        else:
            print(f"  [PASS] eth 组与 trx 组地址无交叠（按 chain 过滤有效）")
    else:
        print("  [FAIL] eth 组或 trx 组为空 —— 无法验证跨链过滤")
        ok = False

    # ★ 量尺有效性：正值+正确地址必须能落账（证明通道可用）
    cleanup()
    h = "i2c1-f1c9-selftest"
    sql("UPDATE wallet SET region = 1, progress = 0 WHERE id = 1;")
    st, txt = post("/app/collect-result", {
        "chain": "tron", "tx_hash": h, "amount": "100", "wallet_id": 1,
        "collected_at": int(time.time() * 1000),
    })
    n = bill_count(h)
    if code_of(txt) == 0 and n == 3:
        print("  量尺有效：不传 to_address 时正常落 3 笔（写入通道可用）")
    else:
        print(f"  [FAIL] 基准请求未落账 (code={code_of(txt)}, bill={n})")
        ok = False

    cleanup()
    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--selftest-assert", action="store_true", dest="selftest_assert")
    args = ap.parse_args()
    if args.selftest_assert:
        return assert_selftest()
    if args.selftest:
        return selftest()

    print("=== F1-C9 to_address 一致性校验（真 HTTP + 真 DB）===")
    # ★ T29 §4-7 响亮提示：防"我以为在测测试库"
    print(f"  ★ 连接目标：DB={DB_NAME}@{DB_PORT}   API={API}")
    cleanup()
    ts = int(time.time() * 1000)

    pub = addr_set_for(0, "trx")
    priv = addr_set_for(2, "trx")
    eth_pub = addr_set_for(0, "eth")
    print(f"公域地址集合(trx): {pub}")
    print(f"私域地址集合(trx): {priv}")
    print(f"公域地址集合(eth): {eth_pub}")
    print("")

    # 取一个具体的公域地址（平台侧）与私域地址 —— 均限 trx 组
    pub_ok_addr = pub[0] if pub else None
    priv_ok_addr = priv[0] if priv else None
    bad_addr = "TOTALLY_WRONG_ADDRESS"
    # 跨链地址：eth 组的地址，用于 tron 请求 ⇒ 应被拒
    cross_chain_addr = eth_pub[0] if eth_pub else bad_addr

    # ★★ WBE01-A 卡A **补覆盖缺口**：原判据声称核"平台/客户/代理三类地址"，但**用例只走到
    #   平台(R1)与私域(R4)** ⇒ `addr_set_for` 的**客户支从未被执行**（实测：翻转后该支产出
    #   空集，而 7/7 仍全 PASS ⇒ 证明无用例触及）。这正是"恒绿的检查＝没有检查"的形态。
    #   ⇒ 补 R7：用**客户(201)的 trx 收款地址**，期望**被拒**。
    #   为什么期望拒绝：按裁定⑤，客户地址须由 `wallet → … → packet.custom_user_id` 解出；
    #     当前**所有 packet 的 custom_user_id 均为 0（未绑定）** ⇒ 解不出客户 ⇒ 服务应拒绝该地址。
    #   ⇒ 对着**未改的业务码**（仍按单租户接受 custom(201) 的地址）跑 ⇒ **R7 必红**（这是真红，
    #     不是恒红）；业务码改完后应转绿。
    _cr = sql_rows("SELECT address FROM settlement WHERE user_id = 201 AND chain LIKE '%trx%';")
    cust_addr = _cr[0][0] if _cr else bad_addr
    print(f"  客户(201) trx 地址（R7 用）: {cust_addr}")

    # ★★ WBE01-A 阶段2「单态断言」修复：R1/R3/R7 的期望**按运行时夹具态取**（见 helper 定义处）。
    bound = fixture_bound()
    _pb, _pr = pub_expect(bound)
    _r7 = r7_expect(bound)
    print("夹具态：packet.custom_user_id<>0 的包 "
          + ("存在 ⇒ 客户支可解（R1/R3 应 3 笔；R7 应接受）"
             if bound else "不存在 ⇒ 客户支不可解（R1/R3 应 2 笔；R7 应拒）"))
    print("")
    cases = [
        # (标签, region, to_address, 期望拒绝, 期望笔数, 期望角色)  ← 期望值按夹具态
        ("R1 公域 + 正确地址(平台,trx)", 1, pub_ok_addr, False, _pb, _pr),
        ("R2 公域 + 错误地址",          1, bad_addr,     True,  0, []),
        ("R3 公域 + 空地址(兼容)",       1, "",           False, _pb, _pr),
        ("R4 私域 + 正确地址(trx)",     2, priv_ok_addr, False, 1, ["4"]),
        ("R5 私域 + 错误地址",          2, bad_addr,     True,  0, []),
        # ★ R6：跨链地址必须被拒（本次实测发现的语义：eth 地址不能用于 tron 归集）
        ("R6 公域 + 跨链地址(eth)",     1, cross_chain_addr, True, 0, []),
        # ★ WBE01-A 卡A 补：客户支覆盖 —— 期望随夹具态翻转（见 helper r7_expect）
        (f"R7 公域 + 客户地址(trx)·{'已绑定应接受' if bound else '未绑定应拒'}",
         1, cust_addr, _r7[0], _r7[1], _r7[2]),
    ]

    # ── 旧断言（逐字保留，勿删 · 承「只翻转并保留留痕」）──────────────────────────
    #   下面三条把「夹具是否绑定」写成了常量 ⇒ 绑定态 R7 恒红、解绑态 R1/R3 恒红。
    #     ("R1 公域 + 正确地址(平台,trx)", 1, pub_ok_addr, False, 3, ["1", "2", "3"]),
    #     ("R3 公域 + 空地址(兼容)",       1, "",           False, 3, ["1", "2", "3"]),
    #     ("R7 公域 + 客户地址(trx)·未绑定应拒", 1, cust_addr, True, 0, []),
    # ──────────────────────────────────────────────────────────────────────────

    for label, region, toaddr, expect_fail, exp_bills, exp_roles in cases:
        sql(f"UPDATE wallet SET region = {region}, progress = 0 WHERE id = 1;")
        h = "i2c1-f1c9-" + label.split()[0]
        body = {"chain": "tron", "tx_hash": h, "amount": "100", "wallet_id": 1,
                "collected_at": ts}
        if toaddr != "":
            body["to_address"] = toaddr
        st, txt = post("/app/collect-result", body)
        c = code_of(txt)
        n = bill_count(h)
        roles = bill_roles(h)

        ok, det = judge(expect_fail, exp_bills, exp_roles, c, n, roles)
        det += f" HTTP={st}" + ("" if not expect_fail else f" msg={txt[:110]}")
        rec(label, ok, det)

    # 附加：确证错误地址不落任何 bill
    h = "i2c1-f1c9-R2"
    rows = sql_rows(f"SELECT role,num FROM bill WHERE transfer_hash = '{h}';")
    rec("附加：R2 无任何 bill 行", len(rows) == 0, f"行数={len(rows)} {rows}")

    cleanup()
    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  to_address 一致性校验生效，兼容与正例不受影响")
    return 0


if __name__ == "__main__":
    sys.exit(main())
