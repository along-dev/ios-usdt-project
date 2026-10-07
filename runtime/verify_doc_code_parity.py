# -*- coding: utf-8 -*-
"""
W-BE-06 判据：**文档-代码 对照闸**（核 `三段业务面审核与等级设计.md` §3 的 9 条对照）。

目标（G-10 / G-13 / P-53 同族）：
  ① 让「报告结论已经过期」**自动可见**，而不是靠人读；
  ② **计数类判据必须同时输出 `count=<n>` 与 `snapshot_sha256=<64hex>`** ——
     把「期望值（写死在文档里的旧数字）」与「磁盘真值（当场算出来的）」分开，
     使「故意改一个文件 ⇒ 哈希变、count 变」**二者同时可见**。

★ 判据放在产物外（`_fix_work/`），不进 `09-docs/`（P-4）。

判据语义（每行 = §3 表格的一行）：
  | 类别 | 含义 | 与报告判定的关系 |
  |---|---|---|
  | `STALE-DOC`    | 报告说「旧文档过时」，本闸断言**现树仍与旧文档矛盾** | 现树仍矛盾 ⇒ MATCH，否则 DRIFT |
  | `CONSISTENT`   | 报告说「一致」，本闸断言**现树确实一致** | 一致 ⇒ MATCH，否则 DRIFT |
  | `TIME-VARYING` | 该数**随时间/运行而变**（如 bill 行数）⇒ **不断言相等**，只打印基线 | 永远不判红，只暴露差值 |
  | `UNVERIFIED`   | 报告自陈「未获独立证据」⇒ 本闸不臆造结论 | 永远不判红，显式 SKIP |

★ `snapshot_sha256` 的算法（本文件内唯一定义，勿在多处复制）：
    对【目录】：对每个文件取 (相对路径, 内容 sha256)，按相对路径排序，
                拼成 `relpath\\tsha256\\n`，再整体 sha256。
    对【单文件】：内容 sha256。
    ⇒ 改名、增删、内容改动、**大小改动**，任一都会使快照哈希变化。

用法：
    python verify_doc_code_parity.py              # 对产物
    python verify_doc_code_parity.py --selftest   # 量尺前置断言（P-5）+ 正/负控
退出码：0 = 全部 MATCH / 非红类；1 = 出现 DRIFT（= 报告 §3 已不再准确）。
"""
from __future__ import annotations

import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import os as _os
import sys as _sys

_os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import argparse
import hashlib
import os
import re
import subprocess
import sys
import tempfile

ROOT = USDT_ROOT
MYSQL = r"X:\_integration\_fix_work\_toolchain\mariadb-11.4.4-winx64\bin\mysql.exe"
DB = "qk_e2e"

REPORT = os.path.join(ROOT, "09-docs", "reports", "三段业务面审核与等级设计.md")


# --------------------------------------------------------------------------
# 量尺：快照哈希 / 计数（唯一定义处）
# --------------------------------------------------------------------------

def _file_sha256(path, _buf=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(_buf)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def snapshot_of(target):
    """返回 (count, snapshot_sha256, note)。
    目录 ⇒ 递归清点文件；文件 ⇒ 单文件；不存在 ⇒ (0, None, 'missing')。"""
    if os.path.isfile(target):
        return 1, _file_sha256(target), ""
    if not os.path.isdir(target):
        return 0, None, "missing"
    entries = []
    for root, _dirs, files in os.walk(target):
        for fn in files:
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, target).replace("\\", "/")
            entries.append((rel, _file_sha256(p)))
    entries.sort(key=lambda x: x[0])
    blob = "".join("%s\t%s\n" % (r, s) for r, s in entries)
    return len(entries), hashlib.sha256(blob.encode("utf-8")).hexdigest(), ""


def count_matches(paths, pattern):
    """在给定文件集合里数正则命中数；同时返回命中的文件清单（供人核对量尺）。"""
    rx = re.compile(pattern, re.M)
    total = 0
    hits = []
    for p in paths:
        if not os.path.isfile(p):
            continue
        with open(p, encoding="utf-8", errors="replace") as fh:
            n = len(rx.findall(fh.read()))
        if n:
            total += n
            hits.append((os.path.relpath(p, ROOT).replace("\\", "/"), n))
    return total, hits


def grep_present(path, pattern):
    if not os.path.isfile(path):
        return False
    with open(path, encoding="utf-8", errors="replace") as fh:
        return re.search(pattern, fh.read(), re.M) is not None


def db_count(sql):
    """查 DB 计数；拿不到 ⇒ None（调用方必须 SKIP，不得回落静态值，P-53）。"""
    if not os.path.isfile(MYSQL):
        return None, "mysql 客户端不存在"
    try:
        r = subprocess.run(
            [MYSQL, "--skip-ssl", "-u", "root", "-h", "127.0.0.1", "-P", "13306",
             "-N", "-B", "-e", sql],
            capture_output=True, text=True, timeout=25, errors="replace")
    except Exception as e:
        return None, "%s" % type(e).__name__
    if r.returncode != 0:
        return None, (r.stderr or "").strip()[:120]
    try:
        return int((r.stdout or "").strip().splitlines()[0]), ""
    except Exception:
        return None, "输出不可解析"


def emit_count(label, count, snap, extra=""):
    """★ 计数类判据的统一输出格式：count 与 snapshot_sha256 必须【并列】。"""
    print("      %s: count=%s snapshot_sha256=%s %s"
          % (label, count, snap if snap else "<n/a>", extra))


# --------------------------------------------------------------------------
# §3 的 9 条对照（逐行实现；expect 抄自报告表格的「判定」列）
# --------------------------------------------------------------------------

def row01_apk():
    """§3-1：旧文档称「0 个 .apk / japapp 目录不存在」；报告判 ❌ 文档过时。"""
    d = os.path.join(ROOT, "06-android", "apk", "japapp")
    japapp = os.path.join(d, "japapp.apk")
    n, snap, note = snapshot_of(d)
    emit_count("06-android/apk/japapp", n, snap, note)
    exists = os.path.isdir(d)
    sz = os.path.getsize(japapp) if os.path.isfile(japapp) else 0
    print("      japapp.apk bytes=%d" % sz)
    actual = "❌" if (exists and n > 0) else "✅"
    return actual, "❌", "dir=%s files=%d" % (exists, n)


def row02_d3c1():
    """§3-2：旧卡称「D3-C1 未落地 / AfterFunc 仍在 / 无持久化」；报告判 ❌ 文档过时。"""
    scan = os.path.join(ROOT, "01-backend-go", "blockchain", "scan.go")
    timer = os.path.join(ROOT, "01-backend-go", "initialize", "timer.go")
    wallet = os.path.join(ROOT, "01-backend-go", "model", "app", "wallet.go")
    a = grep_present(scan, r"wallet\.TurnPubicAt\s*=")
    b = grep_present(timer, r"turn_pubic_at\s*>\s*0")
    c = grep_present(wallet, r"turn_pubic_at")
    print("      scan.go 写 TurnPubicAt=%s · timer.go 持久化查询=%s · wallet 模型有列=%s" % (a, b, c))
    actual = "❌" if (a and b and c) else "✅"
    return actual, "❌", "fix_present=%s" % (a and b and c)


def row03_bindhost():
    """§3-3：旧提示词称「R2-4 未做」；报告判 ❌ 过时。三方 BIND_HOST 必须在位。"""
    trio = {
        "core/server.go": os.path.join(ROOT, "01-backend-go", "core", "server.go"),
        "src_restored/app.js": os.path.join(ROOT, "02-backend-node", "src_restored", "app.js"),
        "_gva_proxy.cjs": IOS_ROOT + r"\_integration\_fix_work\_gva_proxy.cjs",
    }
    got = {}
    for k, p in trio.items():
        got[k] = grep_present(p, r"BIND_HOST")
        print("      %-22s BIND_HOST=%s" % (k, got[k]))
    # ★ _gva_proxy.cjs 在【树外】，缺失时不算失败，但必须显式标出
    in_tree_ok = got["core/server.go"] and got["src_restored/app.js"]
    if not os.path.isfile(trio["_gva_proxy.cjs"]):
        print("      [WARN] 第三方（树外）_gva_proxy.cjs 不存在（3 方只核到 2 方）")
    actual = "❌" if in_tree_ok else "✅"
    return actual, "❌", "in_tree=%s out_of_tree=%s" % (in_tree_ok, got["_gva_proxy.cjs"])


def row04_t22():
    """§3-4：旧文档称「verify_t22 FAIL」；报告判 ❌ 过时。判据已改 SKIP 语义。"""
    p = IOS_ROOT + r"\_integration\_fix_work\verify_t22_bill_endpoint.py"
    skip = grep_present(p, r"SKIP")
    dynamic = grep_present(p, r"_db_bill_count")
    print("      verify_t22: SKIP 语义=%s · 动态取值=%s" % (skip, dynamic))
    actual = "❌" if (skip and dynamic) else "✅"
    return actual, "❌", "skip_semantics=%s" % (skip and dynamic)


def row05_dist():
    """§3-5：旧提示词称「dist 238 文件」；报告判 ❌ 数字不符。★ 计数类。"""
    d = os.path.join(ROOT, "03-web-admin", "dist")
    n, snap, note = snapshot_of(d)
    emit_count("03-web-admin/dist", n, snap, note)
    print("      旧文档声称=238；报告实测=196")
    if n == 0:
        return "SKIP", "❌", "dist 不存在 ⇒ 拿不到真值（P-53：不判 PASS）"
    actual = "❌" if n != 238 else "✅"
    return actual, "❌", "count=%d (doc 238)" % n


def row06_nginx():
    """§3-6：旧提示词称「nginx 模板 7 个 server 块」；报告判 ❌ 量尺错（实为 5）。★ 计数类。"""
    p = os.path.join(ROOT, "08-infra", "nginx", "default.conf.template")
    n, hits = count_matches([p], r"^server\s*\{")
    nup, _ = count_matches([p], r"^upstream\s+\S+\s*\{")
    _cnt, snap, note = snapshot_of(p)
    emit_count("08-infra/nginx/default.conf.template", n, snap,
               "server块=%d upstream块=%d（旧文档 7 = 5 server + 2 upstream 误数）" % (n, nup))
    if not os.path.isfile(p):
        return "SKIP", "❌", "模板不存在 ⇒ 拿不到真值"
    actual = "❌" if n != 7 else "✅"
    return actual, "❌", "server_blocks=%d (doc 7)" % n


def row07_regression_set():
    """§3-7：报告自陈「本轮未跑成 ⇒ 两者均未获独立证据」⇒ 本闸【不臆造】。"""
    out = os.path.join(os.environ.get("TEMP", r"C:\Windows\Temp"),
                       "dsh_regression", "regression_main.json")
    if os.path.isfile(out):
        n, snap, _ = snapshot_of(out)
        emit_count("regression_main.json", n, snap, "(存在，但非独立证据)")
    else:
        print("      regression_main.json 不存在 ⇒ 无本轮运行证据")
    return "⚠️", "⚠️", "UNVERIFIED（报告自陈未获独立证据；本闸不判红）"


def row08_bill():
    """§3-8：文档称 bill=43 行、报告实测 33 行 ⇒ ⚠️ 计数漂移。★ **随时间变** ⇒ 只报基线。"""
    n, err = db_count("SELECT COUNT(*) FROM %s.bill;" % DB)
    if n is None:
        print("      [SKIP] 拿不到 DB 真值（%s）⇒ 不判 PASS（P-53）" % err)
        return "SKIP", "⚠️", "db_unreachable=%s" % err
    emit_count("qk_e2e.bill", n, "n/a(DB 表非文件，无快照哈希)",
               "报告实测=33 · 文档(L049)声称=43")
    # ★ 该数随运行变化 ⇒ 【不断言相等】，仅暴露差值
    if n == 33:
        return "⚠️", "⚠️", "count=%d 与报告一致" % n
    return "⚠️", "⚠️", "count=%d ≠ 报告 33 ⇒ 计数已漂移（应改用基线而非写死期望）" % n


def row09_contracts():
    """§3-9：报告判 ✅ 一致。C-2 的两个锚点必须在位。"""
    resp = os.path.join(ROOT, "01-backend-go", "api", "v1", "response", "response.go")
    lock = os.path.join(ROOT, "01-backend-go", "api", "v1", "app", "collect_lock.go")
    a = grep_present(resp, r"c\.JSON\(http\.StatusOK")
    b = grep_present(lock, r"http\.StatusConflict")
    print("      response.go 恒 200=%s · api/v1/app/collect_lock.go 409=%s" % (a, b))
    actual = "✅" if (a and b) else "❌"
    return actual, "✅", "c2_anchors=%s" % (a and b)


ROWS = [
    ("1", "APK 产物存在（旧文档称不存在）", row01_apk),
    ("2", "D3-C1 修复已落地", row02_d3c1),
    ("3", "三方 BIND_HOST 已实现", row03_bindhost),
    ("4", "verify_t22 已改 SKIP 语义", row04_t22),
    ("5", "dist 文件数（计数类）", row05_dist),
    ("6", "nginx server 块数（计数类）", row06_nginx),
    ("7", "回归集 46/48 或 48/48", row07_regression_set),
    ("8", "bill 行数（计数类·随时间变）", row08_bill),
    ("9", "contracts C-2 与代码一致", row09_contracts),
]


# --------------------------------------------------------------------------
# 量尺前置断言（P-5）+ 正/负控
# --------------------------------------------------------------------------

def selftest():
    print("=== 量尺前置断言（P-5）：snapshot_of 必须能察觉增删改 ===")
    ok = True
    with tempfile.TemporaryDirectory() as td:
        a = os.path.join(td, "a.txt")
        b = os.path.join(td, "sub", "b.txt")
        os.makedirs(os.path.dirname(b))
        with open(a, "w", encoding="utf-8") as fh:
            fh.write("one\n")
        with open(b, "w", encoding="utf-8") as fh:
            fh.write("two\n")

        n0, s0, _ = snapshot_of(td)
        print("  基线: count=%d snapshot_sha256=%s" % (n0, s0))

        # 负控：不动 ⇒ 不变
        n1, s1, _ = snapshot_of(td)
        if (n1, s1) != (n0, s0):
            print("  [FAIL] 负控失败：未改动却变了")
            ok = False
        else:
            print("  [PASS] 负控：未改动 ⇒ count 与哈希均不变")

        # 正控 1：改内容 ⇒ count 不变、哈希变（二者【不同时】可见 count 的敏感度）
        with open(a, "w", encoding="utf-8") as fh:
            fh.write("one-changed\n")
        n2, s2, _ = snapshot_of(td)
        if s2 == s0:
            print("  [FAIL] 正控失败：改了内容哈希却不变")
            ok = False
        else:
            print("  [PASS] 正控(改内容)：哈希变 %s→%s（count %d→%d）"
                  % (s0[:12], s2[:12], n0, n2))
        with open(a, "w", encoding="utf-8") as fh:
            fh.write("one\n")

        # 正控 2：增文件 ⇒ count 与哈希【同时】变（G-10 的验收形态）
        c = os.path.join(td, "c.txt")
        with open(c, "w", encoding="utf-8") as fh:
            fh.write("three\n")
        n3, s3, _ = snapshot_of(td)
        if not (n3 != n0 and s3 != s0):
            print("  [FAIL] 正控失败：增文件后 count/哈希未同时变")
            ok = False
        else:
            print("  [PASS] 正控(增文件)：count=%d→%d 且 snapshot_sha256=%s→%s —— 二者同时可见"
                  % (n0, n3, s0[:12], s3[:12]))

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if not os.path.isfile(REPORT):
        print("[FAIL] 报告不存在: %s" % REPORT)
        print("RESULT=RED")
        return 1
    print("对照源: %s" % REPORT)
    print("")

    drift = []
    print("=" * 78)
    print("§3 九条对照 · 现树复核（判定列抄自报告；MATCH=报告仍准确）")
    print("=" * 78)
    for rid, title, fn in ROWS:
        print("[%s] %s" % (rid, title))
        try:
            actual, expected, detail = fn()
        except Exception as e:
            actual, expected, detail = "ERR", "?", "%s: %s" % (type(e).__name__, e)
        if actual in ("SKIP", "ERR"):
            verdict = "UNVERIFIED"
        elif actual == expected:
            verdict = "MATCH"
        else:
            verdict = "DRIFT"
        if verdict == "DRIFT":
            drift.append(rid)
        print("      → 现树=%s 报告判定=%s ⇒ %s   (%s)" % (actual, expected, verdict, detail))
        print("")

    print("=" * 78)
    if drift:
        print("RESULT=RED  报告 §3 已不再准确的行: %s" % drift)
        print("  ⇒ 处置：更新该行 = 或  在基线中登记为【已知计数漂移】（把期望值与磁盘真值分离）")
        return 1
    print("RESULT=GREEN  报告 §3 九条对照与现树一致（非红类：UNVERIFIED/计数漂移已显式标出）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
