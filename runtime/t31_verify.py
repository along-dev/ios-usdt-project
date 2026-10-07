# -*- coding: utf-8 -*-
"""T31 判据 · **确定性并发**下的重复提交幂等（契约 C-6）。

★ 为什么需要它：`verify_money_path.py` 的并发断言是**背靠背发两条 POST** ⇒ **是否真重叠靠时序运气**
  ⇒ 非确定性（串行命中就 GREEN，真并发撞键才 RED）。本件用 **SQL gap 锁屏障**把"真并发"**变成确定事件**：
    ① 先在**独立连接**上 `START TRANSACTION; SELECT … WHERE transfer_hash=? AND role=<首插role> FOR UPDATE;`
       （对**不存在的行**取**间隙锁** ⇒ 之后任何 INSERT 进该间隙都会**阻塞**）
    ② 再**同时**发两条 POST ⇒ 双双**阻塞在同一间隙锁**上
    ③ 屏障 `COMMIT` 释放 ⇒ 两条 INSERT **同时**放行 ⇒ **恰一条成功、另一条撞 `uk_txhash_role`（1062）**
  ⇒ 无需运气：**并发落败方必然出现**。

★ 断言（T31 §4.3 严格版 ＋ §7.3 的 V6）：
    V1 两条响应**都 `code==0`**
    V2 `bill` **不翻倍**（行数 == 期望：public 3 / private 1）
    V3 `(transfer_hash, role)` **无重复行**
    V4 **恰一次** `duplicated=false`（＝恰一次新建）
    V5 变异（去掉 1062 捕获）⇒ **必红**    ← 由外部对被测二进制做，见驱动
    V6 幂等响应返回的 `bill` id ＝ **「首次那笔」** 的 id，且**两条响应相同**；
       ★ **public 期望 `role=1`、private 期望 `role=4`**（私域那一次正是用来证明**没有硬编码 role=1**）

用法（★ 必须显式注入隔离变量，否则默认值会打业务库/共享 8888）：
    DSH_DB=qk_e2e_test DSH_API=http://127.0.0.1:8900 python t31_verify.py
退出码：0 = V1–V6 全绿；1 = 有红。
"""
from __future__ import annotations

import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

API = os.environ.get("DSH_API", "http://127.0.0.1:8888")
DB = os.environ.get("DSH_DB", "qk_e2e")
assert DB == "qk_e2e_test", "⛔ 拒绝裸跑：只允许隔离库 qk_e2e_test（须经 iso_run.py 注入）"
assert API == "http://127.0.0.1:8900", "⛔ 拒绝裸跑：只允许隔离实例 8900（须经 iso_run.py 注入）"
DB_PORT = "13306"
MYSQL = IOS_ROOT + r"\_integration\_fix_work\_toolchain\mariadb-11.4.4-winx64\bin\mysql.exe"
TOKEN = "i2c1-e2e-token"
BARRIER_HOLD_S = 3          # 间隙锁持有秒数（够两条 POST 都堵上去）

_results = []


def sql(stmt, timeout=60):
    p = subprocess.run([MYSQL, "--skip-ssl", "-h", "127.0.0.1", "-P", DB_PORT, "-u", "root",
                        "--default-character-set=utf8mb4", "-B", "-e", f"USE {DB}; {stmt}"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def rows(stmt):
    rc, out = sql(stmt)
    if rc != 0:
        return []
    ls = [l for l in out.strip().splitlines() if l.strip()]
    return [l.split("\t") for l in ls[1:]] if ls else []


def post(body, timeout=40):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(API + "/app/collect-result", data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Service-Token", TOKEN)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, f"EXC:{e}"


def code_of(txt):
    try:
        return json.loads(txt).get("code")
    except Exception:
        return None


def jbody(txt):
    try:
        return json.loads(txt)
    except Exception:
        return {}


def rec(name, ok, detail):
    _results.append((name, bool(ok), detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def barrier(transfer_hash, role, hold=BARRIER_HOLD_S):
    """★ 间隔锁屏障：在**独立连接**上对 (transfer_hash, role) 的**不存在行**取 `FOR UPDATE` 间隙锁并持有 hold 秒。"""
    stmt = (f"START TRANSACTION; "
            f"SELECT id FROM bill WHERE transfer_hash = '{transfer_hash}' AND role = {role} FOR UPDATE; "
            f"SELECT SLEEP({hold}); COMMIT;")
    return subprocess.Popen([MYSQL, "--skip-ssl", "-h", "127.0.0.1", "-P", DB_PORT, "-u", "root",
                             "--default-character-set=utf8mb4", "-B", "-e", f"USE {DB}; {stmt}"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def run_case(tag, wallet_region, first_role, exp_bills, chain="tron"):
    print(f"\n===== {tag}（wallet.region={wallet_region}，首插 role={first_role}，期望 {exp_bills} 笔）=====")
    h = f"i2c1-t31-{tag}"
    sql(f"DELETE FROM bill WHERE transfer_hash = '{h}';")
    sql(f"UPDATE wallet SET region = {wallet_region}, progress = 0 WHERE id = 1;")
    body = {"chain": chain, "tx_hash": h, "amount": "100", "wallet_id": 1,
            "collected_at": int(time.time() * 1000)}

    # ① 屏障起（占住 (hash, role) 的间隙锁）
    b = barrier(h, first_role)
    time.sleep(1.0)

    # ② 同时发两条 POST（两线程）
    out = {}

    def fire(k):
        out[k] = post(body)

    t1 = threading.Thread(target=fire, args=(1,))
    t2 = threading.Thread(target=fire, args=(2,))
    t0 = time.time()
    t1.start(); t2.start()
    time.sleep(0.3)
    t1.join(timeout=60); t2.join(timeout=60)
    elapsed = time.time() - t0
    b.communicate(timeout=30)

    s1, x1 = out.get(1, (-1, "未回"))
    s2, x2 = out.get(2, (-1, "未回"))
    c1, c2 = code_of(x1), code_of(x2)
    j1, j2 = jbody(x1), jbody(x2)
    b1 = (j1.get("data") or {}).get("billId")
    b2 = (j2.get("data") or {}).get("billId")
    d1 = (j1.get("data") or {}).get("duplicated")
    d2 = (j2.get("data") or {}).get("duplicated")
    rs = [r[0] for r in rows(f"SELECT role FROM bill WHERE transfer_hash = '{h}' ORDER BY id;")]
    n = len(rs)
    dup_pairs = rows(f"SELECT role, COUNT(*) c FROM bill WHERE transfer_hash = '{h}' GROUP BY role HAVING c > 1;")
    minrow = rows(f"SELECT id, role FROM bill WHERE transfer_hash = '{h}' ORDER BY id ASC LIMIT 1;")
    min_id, min_role = (minrow[0][0], minrow[0][1]) if minrow else (None, None)

    print(f"  并发耗时 {elapsed:.2f}s ｜ 响应：c1={c1}(st={s1},bill={b1},dup={d1}) "
          f"c2={c2}(st={s2},bill={b2},dup={d2})")
    print(f"  库：rows={n} roles={rs} ｜ 首行 id={min_id} role={min_role} ｜ 重复 role 组={dup_pairs}")

    rec(f"{tag}·V1 两条响应都 code==0", (c1 == 0) and (c2 == 0), f"c1={c1} c2={c2}")
    rec(f"{tag}·V2 bill 不翻倍", n == exp_bills, f"行数={n}（应 {exp_bills}）")
    rec(f"{tag}·V3 (transfer_hash,role) 无重复行", len(dup_pairs) == 0, f"重复组={dup_pairs}")
    rec(f"{tag}·V4 恰一次 duplicated=false", sum(1 for d in (d1, d2) if d is False) == 1,
        f"dup1={d1} dup2={d2}")
    # V6：两条响应返回**同一**「首次那笔」 id，且其 role 符合预期
    ok_v6 = (b1 is not None) and (b1 == b2) and (str(b1) == str(min_id)) and (str(min_role) == str(first_role))
    rec(f"{tag}·V6 幂等响应＝「首次那笔」(role={first_role})",
        ok_v6, f"bill1={b1} bill2={b2} 库首行 id={min_id} role={min_role}")
    return all(ok for nm, ok, _ in _results if nm.startswith(tag))


def main():
    print(f"=== T31 确定性并发判据 · API={API} · DB={DB} ===")
    # 量尺前置：服务可达 + 库可读
    try:
        with urllib.request.urlopen(API + "/health", timeout=6) as r:
            if r.status != 200:
                print(f"  [FAIL] /health -> {r.status}"); return 2
        print("  [OK] /health 200")
    except Exception as e:
        print(f"  [FAIL] 服务不可达: {e}"); return 2
    ok_pub = run_case("public", 1, 1, 3)
    ok_pri = run_case("private", 2, 4, 1)
    print("")
    fails = [(n, d) for n, o, d in _results if not o]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print("RESULT=RED")
        for n, d in fails:
            print(f"  - {n}: {d}")
        return 1
    print("RESULT=GREEN  T31：并发重复提交已收敛为幂等（C-6 成立）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
