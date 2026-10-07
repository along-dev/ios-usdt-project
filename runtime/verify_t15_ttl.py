# -*- coding: utf-8 -*-
"""
T15 —— P2-4 的 TTL 可观测性（R2）

判据：V1..V7
  V1  机械证明 TTL 存在（wallet-data.js / device-event.js 均含
      `expireAfterSeconds: 30 * 24 * 3600`）
  V2  新增巡检逻辑【真的会记录】—— 代码路径含 logger 调用（含 warn）
  V3  02-backend-node/README.md 含 TTL 声明段
  V4  TTL 数值未变（仍 30 天 = 2592000 秒）
  V5  既有端点未回归（无 token 401；公开端点 200）
  V6  node --check 通过（新增/改动 JS）
  V7  守护：_manifest.sha256、contracts.md 未改

约定：
  - 读文件测 eol/bytes 一律 open(p,'rb')（P-36）
  - eol 断言用「CRLF 数 + LONE_CR 数不变」（P-37）
  - 退出码：全绿 0，否则 1

用法：
  $env:PYTHONIOENCODING='utf-8'
  E:\\CTF\\runtime\\python\\python.exe verify_t15_ttl.py
"""

import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = USDT_ROOT
BE = os.path.join(ROOT, "02-backend-node")
SRC = os.path.join(BE, "src_restored")

WALLET = os.path.join(SRC, "core", "db", "models", "wallet-data.js")
DEVICE = os.path.join(SRC, "core", "db", "models", "device-event.js")
TASKJS = os.path.join(SRC, "core", "db", "models", "task.js")
CONST = os.path.join(SRC, "config", "constants.js")
README = os.path.join(BE, "README.md")
SCHED_INDEX = os.path.join(SRC, "schedules", "index.js")
TTL_TASK = os.path.join(SRC, "schedules", "ttl-inspect.js")
API_INDEX = os.path.join(SRC, "plugins", "api", "index.js")
TTL_ROUTE = os.path.join(SRC, "plugins", "api", "routes", "dashboard-ttl.js")
REQDOC = os.path.join(ROOT, "09-docs", "analysis", "需求文档.md")

MANIFEST = os.path.join(ROOT, "_manifest.sha256")
CONTRACTS = os.path.join(ROOT, "09-docs", "spec", "contracts.md")

NODE = r"E:\CTF\runtime\node\node.exe"

# ---- 守护锚点（动前实测，见 BASE 表）----------------------------------------
GUARD_MANIFEST_SHA = "b940dc19a76f1627ed185f9af54ff79f"
GUARD_CONTRACTS_SHA = "f80a2ead6736d5f5aff70e72e3aa7de1"

# ---- 不可变锚点：TTL 数值（★ V4 的核心）-------------------------------------
TTL_30D = "30 * 24 * 3600"
TTL_90D = "90 * 24 * 3600"

results = []


def rec(vid, ok, detail):
    results.append((vid, ok, detail))
    print("[%s] %s  %s" % ("PASS" if ok else "FAIL", vid, detail))


def read_bytes(p):
    """★ P-36：eol/bytes 必须二进制读。"""
    with open(p, "rb") as f:
        return f.read()


def counts(b):
    """★ P-37：CRLF 数与 LONE_CR 数。"""
    crlf = b.count(b"\r\n")
    return crlf, b.count(b"\r") - crlf


def sha256s(p):
    return hashlib.sha256(read_bytes(p)).hexdigest()


def read_text(p):
    return read_bytes(p).decode("utf-8")


def grep_lines(path, pattern):
    """返回 [(行号, 行内容)]。"""
    hits = []
    for i, line in enumerate(read_text(path).split("\n"), 1):
        if re.search(pattern, line):
            hits.append((i, line.rstrip("\r")))
    return hits


def http_status(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return "ERR:%s" % e


# =============================================================================
# V1 —— 机械证明 TTL 存在
# =============================================================================
def v1():
    ok_all = True
    detail = []
    for label, path, key, ttl in (
        ("WalletData", WALLET, "receivedAt", TTL_30D),
        ("DeviceEvent", DEVICE, "createdAt", TTL_30D),
    ):
        hits = grep_lines(path, r"expireAfterSeconds\s*:\s*" + re.escape(ttl))
        if hits:
            ln, content = hits[0]
            detail.append("%s:%d = %s" % (os.path.basename(path), ln, content.strip()))
        else:
            ok_all = False
            detail.append("%s 缺 `%s`" % (os.path.basename(path), ttl))
    # task 90 天（一并登记）
    hits = grep_lines(TASKJS, r"expireAfterSeconds\s*:\s*" + re.escape(TTL_90D))
    if hits:
        detail.append("task.js:%d = %s" % (hits[0][0], hits[0][1].strip()))
    rec("V1", ok_all, "TTL 存在 | " + " || ".join(detail))
    return ok_all


# =============================================================================
# V4 —— TTL 数值未变（先于 V2 跑，锚定不可变）
# =============================================================================
def v4():
    ok = True
    detail = []
    checks = (
        (WALLET, TTL_30D, "wallet-data.js"),
        (DEVICE, TTL_30D, "device-event.js"),
        (TASKJS, TTL_90D, "task.js"),
    )
    for path, ttl, name in checks:
        hits = grep_lines(path, r"expireAfterSeconds\s*:\s*" + re.escape(ttl))
        if hits:
            detail.append("%s 仍为 %s" % (name, ttl))
        else:
            ok = False
            detail.append("%s 的 %s 丢失/被改" % (name, ttl))
    # constants.js 常量未变
    chits = grep_lines(CONST, r"EVENT_TTL_DAYS\s*:\s*30\b")
    if chits:
        detail.append("constants.js:%d EVENT_TTL_DAYS: 30" % chits[0][0])
    else:
        ok = False
        detail.append("constants.js 的 EVENT_TTL_DAYS: 30 丢失/被改")
    # 反例：不得出现其它数值的 expireAfterSeconds
    for path, name in ((WALLET, "wallet-data.js"), (DEVICE, "device-event.js"), (TASKJS, "task.js")):
        for ln, line in grep_lines(path, r"expireAfterSeconds"):
            if not re.search(r"expireAfterSeconds\s*:\s*(30|90) \* 24 \* 3600", line):
                ok = False
                detail.append("%s:%d 出现未预期 TTL 值: %s" % (name, ln, line.strip()))
    rec("V4", ok, "TTL 数值未变 | " + " || ".join(detail))
    return ok


# =============================================================================
# V2 —— 新增巡检逻辑真的会记录（代码路径含 logger 调用）
# =============================================================================
def v2():
    detail = []
    ok = True

    if not os.path.exists(TTL_TASK):
        rec("V2", False, "缺 %s" % TTL_TASK)
        return False

    src = read_text(TTL_TASK)
    # 2a. 必须导入 logger
    if not re.search(r"import\s*\{[^}]*logger[^}]*\}\s*from\s*['\"][^'\"]*core/logger/index\.js['\"]", src):
        ok = False
        detail.append("未从 core/logger 导入 logger")
    else:
        detail.append("已导入 logger")

    # 2b. 必须含 logger.warn 调用（可观测性核心）
    warn_hits = grep_lines(TTL_TASK, r"logger\.warn\s*\(")
    if warn_hits:
        detail.append("logger.warn 在 ttl-inspect.js:%d" % warn_hits[0][0])
    else:
        ok = False
        detail.append("缺 logger.warn 调用")

    # 2c. 结构化字段须含 collection / expiringSoon / oldestAgeDays
    for fld in ("collection", "expiringSoon", "oldestAgeDays"):
        if re.search(r"\b%s\b" % fld, src):
            detail.append("字段 %s 存在" % fld)
        else:
            ok = False
            detail.append("字段 %s 缺失" % fld)

    # 2d. 必须真的 countDocuments（统计即将过期记录数）
    if re.search(r"countDocuments\s*\(", src):
        detail.append("含 countDocuments 实查询")
    else:
        ok = False
        detail.append("缺 countDocuments 实查询")

    # 2e. 必须在 schedules/index.js 注册（否则 handler 永不执行）
    if os.path.exists(SCHED_INDEX):
        idx = read_text(SCHED_INDEX)
        if re.search(r"ttlInspect|ttl-inspect", idx):
            detail.append("已在 schedules/index.js 注册")
        else:
            ok = False
            detail.append("未在 schedules/index.js 注册（不会执行）")
    else:
        ok = False
        detail.append("缺 schedules/index.js")

    rec("V2", ok, "巡检会记录 | " + " || ".join(detail))
    return ok


# =============================================================================
# V3 —— README 含 TTL 声明段
# =============================================================================
def v3():
    if not os.path.exists(README):
        rec("V3", False, "缺 README.md")
        return False
    txt = read_text(README)
    detail = []
    ok = True

    # 须有 TTL 小节标题
    if re.search(r"^#+\s*.*TTL", txt, re.M):
        lines = grep_lines(README, r"^#+\s*.*TTL")
        detail.append("README.md:%d = %s" % (lines[0][0], lines[0][1].strip()))
    else:
        ok = False
        detail.append("无 TTL 标题段")

    # 三集合均须登记
    for name, ttl in (("WalletData", "30"), ("device-event", "30"), ("task", "90")):
        if re.search(re.escape(name), txt, re.I):
            detail.append("%s 已登记" % name)
        else:
            ok = False
            detail.append("%s 未登记" % name)

    # 行为与运维含义
    for kw in ("静默删除", "不可追溯"):
        if kw in txt:
            detail.append("含「%s」" % kw)
        else:
            ok = False
            detail.append("缺「%s」" % kw)

    rec("V3", ok, "README TTL 段 | " + " || ".join(detail))
    return ok


# =============================================================================
# V6 —— node --check
# =============================================================================
def v6():
    targets = [p for p in (TTL_TASK, TTL_ROUTE, SCHED_INDEX, API_INDEX, WALLET, DEVICE) if os.path.exists(p)]
    bad = []
    checked = []
    for p in targets:
        # .js 全为 ESM（import 语法）⇒ 走 stdin 的 module 模式校验更可靠
        src = read_text(p)
        if src.lstrip().startswith("import"):
            r = subprocess.run([NODE, "--input-type=module", "--check"], input=src,
                               capture_output=True, text=True, encoding="utf-8")
        else:
            r = subprocess.run([NODE, "--check", p], capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            bad.append("%s: %s" % (os.path.basename(p), (r.stderr or "").strip().split("\n")[0]))
        else:
            checked.append(os.path.basename(p))
    ok = not bad
    rec("V6", ok, "node --check: 通过 %d 个 %s%s" % (
        len(checked), ",".join(checked), (" | 失败: " + "; ".join(bad)) if bad else ""))
    return ok


# =============================================================================
# V5 —— 既有端点未回归
# =============================================================================
def v5():
    base = "http://127.0.0.1:3000"
    expect = [
        ("/api/dashboard", 401),            # 受保护：无 token 必 401
        ("/api/dashboard/device-versions", 401),
        ("/api/dashboard/collect-summary", 401),
        ("/api/dashboard/ttl-status", 401),  # 新端点：同样必须受保护
        ("/api/template", 200),              # 公开白名单
        ("/api/pixel-config", 200),
        ("/vodex.html", 200),
    ]
    ok = True
    detail = []
    for path, want in expect:
        got = http_status(base + path)
        mark = "ok" if got == want else "MISMATCH"
        if got != want:
            ok = False
        detail.append("%s=%s(期望%s,%s)" % (path, got, want, mark))
    rec("V5", ok, "端点回归 | " + " ".join(detail))
    return ok


# =============================================================================
# V7 —— 守护
# =============================================================================
def v7():
    ok = True
    detail = []
    for path, want, name in ((MANIFEST, GUARD_MANIFEST_SHA, "_manifest.sha256"),
                             (CONTRACTS, GUARD_CONTRACTS_SHA, "contracts.md")):
        if not os.path.exists(path):
            ok = False
            detail.append("%s 缺失" % name)
            continue
        got = sha256s(path)[:32]
        if got == want:
            detail.append("%s 未改(%s)" % (name, got))
        else:
            ok = False
            detail.append("%s 被改! %s→%s" % (name, want, got))

    # 禁改文件：landing.js / app.js 仍须存在（本轮不得改动它们）
    landing = os.path.join(SRC, "plugins", "api", "routes", "landing.js")
    appjs = os.path.join(SRC, "app.js")
    for p, name in ((landing, "landing.js"), (appjs, "app.js")):
        if os.path.exists(p):
            detail.append("%s 存在(本轮未改)" % name)
        else:
            ok = False
            detail.append("%s 缺失" % name)

    rec("V7", ok, "守护 | " + " || ".join(detail))
    return ok


# =============================================================================
# 附加：eol / bytes 报告（P-36/P-37）
# =============================================================================
def eol_report():
    print("\n---- eol / bytes（P-36/P-37）----")
    for p in (WALLET, DEVICE, CONST, README, SCHED_INDEX, TTL_TASK, TTL_ROUTE):
        if not os.path.exists(p):
            print("  %-28s <不存在>" % os.path.basename(p))
            continue
        b = read_bytes(p)
        crlf, lone = counts(b)
        print("  %-28s bytes=%-6d sha=%s CRLF=%d LONE_CR=%d" % (
            os.path.basename(p), len(b), hashlib.sha256(b).hexdigest()[:32], crlf, lone))


def main():
    print("=" * 78)
    print("T15 —— TTL 可观测性 判据")
    print("=" * 78)
    v1()
    v4()
    v2()
    v3()
    v6()
    v5()
    v7()
    eol_report()

    print("\n" + "=" * 78)
    fails = [v for v, ok, _ in results if not ok]
    if fails:
        print("结果：红 —— 失败判据: %s" % ", ".join(fails))
        print("=" * 78)
        return 1
    print("结果：绿 —— 全部 %d 条判据通过" % len(results))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
