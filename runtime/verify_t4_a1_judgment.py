#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T4 / R3 判据脚本 —— A1 coruna 17.3+ 的前置判定（确认 + 灰度实测方案）

机械证明："group.html 无上界版本拒绝"（V1+V2 为核心）。

断言：
  V1  group.html 的唯一版本 return 是下界 13E4 (return 1001)
  V2  :558 的 CORUNA_MAX_IOS 分支【不含 return】（仅 WARN）
  V3  C3_前置判定报告.md 存在且含核心结论句
  V4  A1_灰度实测方案.md 存在且含 6 个步骤
  V5  未改任何产物（platform_module.js / group.html sha256 未变）
  V6  脚本自带 --selftest（P-5）
  V7  守护：_manifest.sha256、contracts.md 未改

用法：
  python verify_t4_a1_judgment.py
  python verify_t4_a1_judgment.py --selftest

环境：本机无 pwsh，用 python 直跑；读文件一律用 open(p,'rb')（P-36）。
"""

import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib
import os
import re
import sys

# ---------------------------------------------------------------------------
# 路径与基线（sha256 为本卡编制时现场重取）
# ---------------------------------------------------------------------------
ROOT = USDT_ROOT

GROUP_HTML = os.path.join(ROOT, "05-ios", "coruna", "group.html")
PLATFORM_MODULE = os.path.join(ROOT, "05-ios", "coruna", "platform_module.js")
REPORT = os.path.join(ROOT, "09-docs", "reports", "C3_前置判定报告.md")
PLAN = os.path.join(ROOT, "09-docs", "reports", "A1_灰度实测方案.md")
MANIFEST = os.path.join(ROOT, "_manifest.sha256")
CONTRACTS = os.path.join(ROOT, "09-docs", "spec", "contracts.md")

# ★ 本卡 base 中的 group.html 基线（卡里明文）
GROUP_HTML_SHA256 = "af41641e788ac5ae921f8afa7a94f4ac30d3fb655161baa98b54e363e2649307"
GROUP_HTML_BYTES = 50911

# ★ 编制时现场重取的产物基线（V5）
PLATFORM_MODULE_SHA256 = "2d16f1d5fef31014ea6e04b974ac6e724d03155e756b2e79a2d841dd9008ddb0"
PLATFORM_MODULE_BYTES = 33674

# ★ 守护基线（V7）
MANIFEST_SHA256 = "b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2"
CONTRACTS_SHA256 = "f80a2ead6736d5f5aff70e72e3aa7de1c7cc63f93a604fb6eeb4a163059f925c"

# ★ 报告核心结论句（V3；允许跨行空白差异）
REPORT_CORE = "它落在\"静默复用 17.0 配置\"的盲区里"
REPORT_CORE_ALT = "盲区里"
REPORT_MUST_HAVE = [
    "不要",          # "不要在未验证前改偏移表"
    "Stage1",
]

# ★ 方案的 6 个步骤（V4）
PLAN_STEPS = [
    "步骤一：设备选取",
    "步骤二：观测点",
    "步骤三：判定规则",
    "步骤四：数据记录",
    "步骤五：回归约束",
    "步骤六：前置条件与登记",
]


def read_bytes(path):
    """P-36：一律用 rb 读，避免 eol 转换污染。"""
    with open(path, "rb") as f:
        return f.read()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def read_text(path):
    """解码为文本，不做 eol 归一（保留 \\n 切分即可，group.html 为 LF）。"""
    return read_bytes(path).decode("utf-8")


def eol_stats(b):
    """P-37：返回 (CRLF 数, LONE_CR 数, LF 数)。"""
    crlf = b.count(b"\r\n")
    cr = b.count(b"\r")
    lf = b.count(b"\n")
    return crlf, cr - crlf, lf


# ---------------------------------------------------------------------------
# V1 / V2：核心机械断言
# ---------------------------------------------------------------------------
def find_return_1001(text):
    """返回所有 `return 1001` 的 (行号, 行内容)。"""
    out = []
    for i, line in enumerate(text.split("\n"), 1):
        if re.search(r"\breturn\s+1001\b", line):
            out.append((i, line.rstrip()))
    return out


def extract_block(lines, start_lineno):
    """从 start_lineno（1-based，应为 `if (...) {` 行）起，按花括号配平取出整块。

    返回 (块内行列表, (起行号, 止行号))。用于 V2 判定 :558 分支体内是否含 return。
    """
    depth = 0
    started = False
    body = []
    for j in range(start_lineno - 1, len(lines)):
        line = lines[j]
        body.append((j + 1, line.rstrip()))
        depth += line.count("{") - line.count("}")
        if "{" in line:
            started = True
        if started and depth == 0:
            return body, (start_lineno, j + 1)
    return body, (start_lineno, len(lines))


def check_v1(text):
    """V1：唯一版本 return 是下界 13E4。"""
    lines = text.split("\n")
    hits = find_return_1001(text)

    # 定位下界门禁行
    lower = None
    for i, line in enumerate(lines, 1):
        if "13E4" in line and "iOSVersion" in line and "return 1001" in line:
            lower = (i, line.rstrip())
            break

    ok = lower is not None
    detail = []
    detail.append("  `return 1001` 全部出现位置（行号: 内容）:")
    for ln, c in hits:
        detail.append("    :%d  %s" % (ln, c.strip()[:130]))
    if lower:
        detail.append("  ★ 版本下界门禁: :%d  (13E4 == 130000 == iOS 13.0)" % lower[0])
    else:
        detail.append("  ★ 未找到 13E4 下界门禁行")

    # 下界门禁必须是 return 1001 中【最靠前】的那条，且行内含 13E4
    if hits and lower:
        first = hits[0][0]
        if first != lower[0]:
            ok = False
            detail.append("  ✗ 首个 return 1001 在 :%d，不是 13E4 门禁 :%d" % (first, lower[0]))

    return ok, "\n".join(detail), {"lower_gate_line": lower[0] if lower else None, "returns": hits}


def check_v2(text):
    """V2：:558 的 CORUNA_MAX_IOS 分支不含 return。"""
    lines = text.split("\n")

    # 定位 CORUNA_MAX_IOS 比较行
    gate = None
    for i, line in enumerate(lines, 1):
        if "CORUNA_MAX_IOS" in line and "iOSVersion >" in line and "{" in line:
            gate = i
            break
    if gate is None:
        return False, "  ✗ 未找到 `iOSVersion > CORUNA_MAX_IOS {` 分支", {}

    body, span = extract_block(lines, gate)
    inner = "\n".join(l for _, l in body[1:-1])  # 去掉 if 行与收尾 }

    # 分支体内不得有 return / 1001 / 1003
    has_return = bool(re.search(r"\breturn\b", inner))
    has_1001 = "1001" in inner
    has_1003 = "1003" in inner
    warn_lines = [n for n, l in body if "window.log" in l or "console.warn" in l or "reportTelemetry" in l]

    ok = (not has_return) and (not has_1001) and (not has_1003) and len(warn_lines) > 0

    detail = []
    detail.append("  ★ 分支定位: :%d  `%s`" % (gate, lines[gate - 1].strip()[:110]))
    detail.append("  ★ 分支体范围: :%d – :%d（共 %d 行）" % (span[0], span[1], len(body)))
    detail.append("  分支体全文:")
    for n, l in body:
        detail.append("    %d  %s" % (n, l.strip()[:130]))
    detail.append("  ── 机械判据 ──")
    detail.append("  分支体内含 `return` : %s   （须为 False）" % has_return)
    detail.append("  分支体内含 `1001`   : %s   （须为 False）" % has_1001)
    detail.append("  分支体内含 `1003`   : %s   （须为 False）" % has_1003)
    detail.append("  仅告警调用行        : %s   （须非空 ⇒ 确是 WARN 而非 return）" % warn_lines)

    metas = {"gate_line": gate, "span": span, "return": has_return, "1001": has_1001, "1003": has_1003}
    return ok, "\n".join(detail), metas


def scan_other_upper_bound(text):
    """停靠点2 检查：是否存在【其他】上界拒绝。

    启发式：查找形如 `iOSVersion > 常量` 且同一分支体内有 return 的位置。
    :558 自身排除（它是 WARN）。
    """
    lines = text.split("\n")
    found = []
    for i, line in enumerate(lines, 1):
        if re.search(r"iOSVersion\s*>", line) and "{" in line and "CORUNA_MAX_IOS" not in line:
            body, span = extract_block(lines, i)
            inner = "\n".join(l for _, l in body)
            if re.search(r"\breturn\b\s*(1001|1003|)", inner) and "return" in inner:
                found.append((i, line.strip(), span))
    return found


# ---------------------------------------------------------------------------
# V3 / V4：文档断言
# ---------------------------------------------------------------------------
def check_v3():
    if not os.path.exists(REPORT):
        return False, "  ✗ 报告不存在: %s" % REPORT
    txt = read_text(REPORT)
    b = read_bytes(REPORT)
    crlf, lone_cr, lf = eol_stats(b)
    hits = [s for s in [REPORT_CORE, REPORT_CORE_ALT] if s in txt]
    missing = [s for s in REPORT_MUST_HAVE if s not in txt]
    ok = bool(hits) and not missing
    detail = []
    detail.append("  ★ 报告存在: %s" % REPORT)
    detail.append("  ★ 字节数: %d ; EOL: CRLF=%d LONE_CR=%d LF=%d" % (len(b), crlf, lone_cr, lf))
    detail.append("  ★ 核心结论句命中: %s" % hits)
    if missing:
        detail.append("  ✗ 缺失关键片段: %s" % missing)
    # 批注块自检
    annotated = "★ 有效性复核" in txt
    detail.append("  ★ 含『有效性复核』批注块: %s" % annotated)
    return ok, "\n".join(detail), {"annotated": annotated, "bytes": len(b)}


def check_v4():
    if not os.path.exists(PLAN):
        return False, "  ✗ 方案不存在: %s" % PLAN
    txt = read_text(PLAN)
    b = read_bytes(PLAN)
    crlf, lone_cr, lf = eol_stats(b)
    missing = [s for s in PLAN_STEPS if s not in txt]
    # 步骤标题可能写作 "## 1. 步骤一：设备选取"
    ok = not missing
    detail = []
    detail.append("  ★ 方案存在: %s" % PLAN)
    detail.append("  ★ 字节数: %d ; EOL: CRLF=%d LONE_CR=%d LF=%d" % (len(b), crlf, lone_cr, lf))
    detail.append("  ★ 6 步命中: %d/6" % (len(PLAN_STEPS) - len(missing)))
    if missing:
        detail.append("  ✗ 缺失步骤: %s" % missing)
    # 关键判据句
    for key in ["Stage1 失败", "值得补表", "不含真机"]:
        detail.append("  ★ 含关键表述 %-12s : %s" % (key, key in txt))
    return ok, "\n".join(detail), {"bytes": len(b)}


# ---------------------------------------------------------------------------
# V5 / V7：不动产物
# ---------------------------------------------------------------------------
def check_hash(path, want_sha, want_bytes, label):
    if not os.path.exists(path):
        return False, "  ✗ %s 不存在: %s" % (label, path)
    b = read_bytes(path)
    got = sha256_bytes(b)
    ok = (got == want_sha) and (len(b) == want_bytes)
    detail = []
    detail.append("  %s" % path)
    detail.append("    bytes : %d (期望 %d) %s" % (len(b), want_bytes, "OK" if len(b) == want_bytes else "✗"))
    detail.append("    sha256: %s" % got)
    detail.append("    期望  : %s  %s" % (want_sha, "OK" if got == want_sha else "✗ 已变"))
    return ok, "\n".join(detail), {"sha256": got, "bytes": len(b)}


def check_v5():
    ok1, d1, m1 = check_hash(GROUP_HTML, GROUP_HTML_SHA256, GROUP_HTML_BYTES, "group.html")
    ok2, d2, m2 = check_hash(PLATFORM_MODULE, PLATFORM_MODULE_SHA256, PLATFORM_MODULE_BYTES, "platform_module.js")
    ok = ok1 and ok2
    detail = []
    detail.append("  ── 产物未改证据（V5：不改偏移表）──")
    detail.extend([d1, d2])
    return ok, "\n".join(detail), {"group": m1, "platform": m2}


def check_v7():
    if not os.path.exists(MANIFEST):
        return False, "  ✗ 缺少 %s" % MANIFEST
    if not os.path.exists(CONTRACTS):
        return False, "  ✗ 缺少 %s" % CONTRACTS
    bm = read_bytes(MANIFEST)
    bc = read_bytes(CONTRACTS)
    mh = sha256_bytes(bm)
    ch = sha256_bytes(bc)
    ok = (mh == MANIFEST_SHA256) and (ch == CONTRACTS_SHA256)
    detail = []
    detail.append("  _manifest.sha256 : %d B  %s  %s" % (len(bm), mh, "OK" if mh == MANIFEST_SHA256 else "✗ 已变"))
    detail.append("  contracts.md     : %d B  %s  %s" % (len(bc), ch, "OK" if ch == CONTRACTS_SHA256 else "✗ 已变"))
    return ok, "\n".join(detail), {"manifest": mh, "contracts": ch}


def check_v6():
    """V6：脚本自带 --selftest（P-5）。"""
    src = read_text(os.path.abspath(__file__))
    ok = "--selftest" in src and "def selftest" in src
    return ok, "  脚本含 --selftest 入口: %s" % ok, {}


# ---------------------------------------------------------------------------
# selftest（P-5）
# ---------------------------------------------------------------------------
def selftest():
    print("=== SELFTEST (P-5) ===")
    fails = []

    def t(name, cond):
        print("  [%s] %s" % ("PASS" if cond else "FAIL", name))
        if not cond:
            fails.append(name)

    # 1) 纯文本机械判据：合成样本，不触碰真实产物
    sample = "\n".join([
        "function triggerExploit() {",
        "  if (13E4 > platformModule.platformState.iOSVersion) return 1001;",
        "  const CORUNA_MAX_IOS = 170300;",
        "  if (platformModule.platformState.iOSVersion > CORUNA_MAX_IOS) {",
        "    window.log(`WARN: exceeds max`);",
        "  }",
        "  return 0;",
        "}",
    ])
    ok1, _, m1 = check_v1(sample)
    t("V1 在合成样本上识别 13E4 下界", ok1)
    ok2, _, m2 = check_v2(sample)
    t("V2 在合成样本上判定 :4 分支为 WARN 无 return", ok2)

    # 2) 反例：上界分支带 return ⇒ V2 必须失败
    bad = "\n".join([
        "  if (platformModule.platformState.iOSVersion > CORUNA_MAX_IOS) {",
        "    return 1001;",
        "  }",
    ])
    ok3, _, m3 = check_v2(bad)
    t("V2 反例（上界 return）被正确判为 FAIL", not ok3)

    # 3) 反例：上界门禁排在 13E4 之前 ⇒ V1 必须失败
    bad2 = "\n".join([
        "  if (18E4 < platformModule.platformState.iOSVersion) return 1001;",
        "  if (13E4 > platformModule.platformState.iOSVersion) return 1001;",
    ])
    ok4, _, m4 = check_v1(bad2)
    t("V1 反例（存在更早的 return 1001）被正确判为 FAIL", not ok4)

    # 4) eol 统计自检（P-37）
    t("eol_stats 正确分解 CRLF/LONE_CR/LF",
      eol_stats(b"a\r\nb\r\nc\n") == (2, 0, 3))
    t("eol_stats 识别孤立 CR", eol_stats(b"a\rb\n") == (0, 1, 1))

    # 5) sha256 自检
    t("sha256 对空串正确", sha256_bytes(b"") ==
      "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

    print("=== SELFTEST %s (%d fail) ===" % ("PASS" if not fails else "FAIL", len(fails)))
    return 0 if not fails else 1


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    if "--selftest" in sys.argv:
        return selftest()

    print("=" * 74)
    print("T4 / R3 判据 —— A1 coruna 17.3+ 前置判定（确认 + 灰度实测方案）")
    print("=" * 74)

    results = []

    # --- 前置：读源 ---
    if not os.path.exists(GROUP_HTML):
        print("FATAL: 缺少 %s" % GROUP_HTML)
        return 2
    group_text = read_text(GROUP_HTML)

    print("\n--- V1  group.html 的唯一版本 return 是下界 13E4 ---")
    ok, det, meta1 = check_v1(group_text)
    print(det)
    print("  V1: %s" % ("PASS" if ok else "FAIL"))
    results.append(("V1", ok))

    print("\n--- V2  :558 的 CORUNA_MAX_IOS 分支不含 return（仅 WARN）---")
    ok, det, meta2 = check_v2(group_text)
    print(det)
    print("  V2: %s" % ("PASS" if ok else "FAIL"))
    results.append(("V2", ok))

    print("\n--- 停靠点2 检查：是否存在【其他】上界拒绝 ---")
    others = scan_other_upper_bound(group_text)
    if others:
        print("  ✗ 发现其他上界拒绝分支:")
        for ln, c, span in others:
            print("    :%d %s  span=%s" % (ln, c[:110], span))
    else:
        print("  OK 未发现其他上界拒绝（除 :%d 的 WARN）" % meta2.get("gate_line", 0))
    results.append(("STOP2", not others))

    print("\n--- V3  C3_前置判定报告.md 存在且含核心结论句 ---")
    ok, det, _ = check_v3()
    print(det)
    print("  V3: %s" % ("PASS" if ok else "FAIL"))
    results.append(("V3", ok))

    print("\n--- V4  A1_灰度实测方案.md 存在且含 6 个步骤 ---")
    ok, det, _ = check_v4()
    print(det)
    print("  V4: %s" % ("PASS" if ok else "FAIL"))
    results.append(("V4", ok))

    print("\n--- V5  未改任何产物 ---")
    ok, det, _ = check_v5()
    print(det)
    print("  V5: %s" % ("PASS" if ok else "FAIL"))
    results.append(("V5", ok))

    print("\n--- V6  脚本自带 --selftest ---")
    ok, det, _ = check_v6()
    print(det)
    print("  V6: %s" % ("PASS" if ok else "FAIL"))
    results.append(("V6", ok))

    print("\n--- V7  守护：_manifest.sha256 / contracts.md 未改 ---")
    ok, det, _ = check_v7()
    print(det)
    print("  V7: %s" % ("PASS" if ok else "FAIL"))
    results.append(("V7", ok))

    print("\n" + "=" * 74)
    npass = sum(1 for _, v in results if v)
    for k, v in results:
        print("  %-6s %s" % (k, "PASS" if v else "FAIL"))
    print("=" * 74)
    print("TOTAL %d/%d PASS" % (npass, len(results)))
    rc = 0 if npass == len(results) else 1
    print("EXIT %d" % rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())
