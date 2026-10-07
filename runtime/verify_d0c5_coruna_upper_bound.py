# -*- coding: utf-8 -*-
"""
D0-C5 判据：coruna group.html 须有版本上界告警，且【不得改变放行行为】。

★★ 缺陷（调度实测确证，2026-09-29）：
   group.html:462-463
       // Version check: must be >= 130000 (iOS 13.0)
       if (13E4 > platformModule.platformState.iOSVersion) return 1001;
   ⇒ 全文件【只有下界，无上界】。
   而 platform_module.js 的偏移表最高项为 170300（iOS 17.3）
   ⇒ iOS >17.3 的设备【静默复用 17.0 配置】（V0 D-3 描述的形态）。

★ D-3 裁决边界：**不改偏移表、不改放行行为，只加显式告警**
   ⇒ 本判据的 U3 专门守住这条：上界分支内【不得有 return】。

用法：
    python verify_d0c5_coruna_upper_bound.py              # 全量
    python verify_d0c5_coruna_upper_bound.py --selftest   # 量尺前置断言（P-5）

退出码：0 = 全绿；非 0 = 有红。
"""
from __future__ import annotations

# ★ X3：本脚本【自带】UTF-8 输出，不依赖调用方设置 PYTHONIOENCODING（P-10）
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
    pass  # 旧版 Python 无 reconfigure 时静默降级
import argparse
import hashlib
import os
import re
import sys

ROOT = USDT_ROOT + r"\05-ios\coruna"
GROUP = os.path.join(ROOT, "group.html")

# ★ BASE_SHA 的用途（B 路审核指出命名有歧义，此处澄清）：
#   它是【基线锚点】，用来在报告中【区分"尚未改动"与"已改动"】，
#   例如输出「（= base 值，尚未改动）」。
#   ⇒ 改动落地后它【必然】不等于现值，这是预期，不是失效。
#   ★ 它【不】用于"检测第三方篡改" —— 那需要外部可信锚点（本仓库无 git）。
BASE_SHA = "96e094d2c93bcf8d7a265d192a6eb845f561d18b3c8c1a7e357e72f94e777cb6"

_results = []


def rec(name, ok, detail):
    _results.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def read(p):
    return open(p, encoding="utf-8", errors="replace").read()


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def list_js_dylib(root):
    out = []
    for dp, dn, fns in os.walk(root):
        for fn in fns:
            if fn.endswith((".js", ".dylib")):
                out.append(os.path.join(dp, fn))
    return sorted(out)


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True

    if not os.path.isfile(GROUP):
        print(f"  [FAIL] group.html 缺失: {GROUP}")
        return 2
    src = read(GROUP)
    print(f"  group.html 大小: {os.path.getsize(GROUP)} B")

    # 1) 下界必须存在（否则文件被换）
    if "13E4" in src:
        print("  前提成立：存在下界检查 13E4")
    else:
        print("  [WARN] 未找到 13E4 —— 文件可能已变")

    # 2) ★ 量尺有效性（修正版，2026-09-29 自查）：
    #    初版用 `console\.warn` 同时匹配两个样本 ⇒ 【两边都命中】⇒ 恒真，证明不了任何事。
    #    正确的量尺必须证明【能区分】：
    #      (a) U3 用的 return 检测 —— 有 return 的样本命中、无 return 的不命中；
    #      (b) U1 用的上界检测 —— 含 170300 的命中、不含的不命中。
    ret_pat = re.compile(r"\breturn\b")
    with_ret = "if (v > 170300) { console.warn('x'); return 1001; }"
    without_ret = "if (v > 170300) { console.warn('x'); }"
    ok_a = bool(ret_pat.search(with_ret)) and not bool(ret_pat.search(without_ret))
    up_pat = re.compile(r"170300")
    ok_b = bool(up_pat.search(with_ret)) and not bool(up_pat.search("if (v > 130000) {}"))
    if ok_a and ok_b:
        print("  模式有效：return 检测与上界检测均可区分正反样本")
    else:
        print(f"  [FAIL] 模式失效（return区分={ok_a} 上界区分={ok_b}）")
        ok = False

    # 3) 对照：platform_module.js 的偏移表最高项（供 U1 阈值核对）
    pm = os.path.join(ROOT, "platform_module.js")
    if os.path.isfile(pm):
        s = read(pm)
        nums = re.findall(r"\b(1[0-9]{5})\b", s)
        uniq = sorted(set(nums), key=lambda x: int(x))
        top = uniq[-1] if uniq else "?"
        print(f"  platform_module.js 中 6 位版本号最高项: {top}")
    else:
        print("  [WARN] platform_module.js 不存在（阈值须另找）")

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== D0-C5 coruna 上界告警判据 ===")
    print("")

    src = read(GROUP)
    cur = sha256(GROUP)
    print(f"group.html sha256: {cur[:16]}…  ({os.path.getsize(GROUP)} B)")
    if cur == BASE_SHA:
        print("  （= base 值，尚未改动）")
    print("")

    # ---- U1: 存在上界判断 ----
    print("U1 须存在版本上界判断:")
    # 允许 170300 或引用常量（CORUNA_MAX 等）
    has_upper_literal = "170300" in src
    has_upper_const = re.search(r"(MAX_IOS|MAX_VERSION|UPPER_BOUND|OFFSET_MAX)", src) is not None
    has_upper = has_upper_literal and (has_upper_const or re.search(r">\s*17", src) is not None)
    rec("U1 含上界判断（170300 + 比较）", has_upper,
        f"literal_170300={has_upper_literal} const={has_upper_const}"
        + ("" if has_upper else "  ★ 无上界 ⇒ 仍静默复用"))

    # ---- U2: 上界分支内有显式告警 ----
    print("")
    print("U2 上界分支内须有显式告警:")
    # 截取上界判断附近 ±30 行的窗口
    idx = src.find("170300")
    window = src[max(0, idx - 400): idx + 900] if idx >= 0 else ""
    has_warn = bool(re.search(r"console\.warn", window))
    has_tel = bool(re.search(r"reportTelemetry\s*\(", window))
    rec("U2 含 console.warn 或 reportTelemetry（上界分支附近）", has_warn or has_tel,
        f"console.warn={has_warn} reportTelemetry={has_tel}")

    # ---- U3: ★ 不得有 return（D-3 边界）----
    print("")
    print("U3 ★ 上界分支内【不得】有 return（不得改变放行行为，D-3 边界）:")
    # 定位上界 if 块
    m = re.search(
        r"if\s*\([^)]*(?:170300|MAX_IOS|MAX_VERSION|UPPER_BOUND)[^)]*\)\s*\{(.*?)\n\s*\}",
        src, re.S)
    blk = m.group(1) if m else ""
    has_return = bool(re.search(r"\breturn\b", blk))
    if not m:
        rec("U3 上界分支内无 return", False,
            "★ 未能定位上界 if 块（可能写法不同，须人工确认）")
    else:
        rec("U3 上界分支内无 return", not has_return,
            "OK（未改变放行行为）" if not has_return
            else "★ 含 return ⇒ 改变了门禁行为，超出 D-3 范围")

    # ---- U4: 下界仍存在 ----
    print("")
    print("U4 防改过头：下界检查仍存在:")
    rec("U4 仍含下界 13E4", "13E4" in src, "OK" if "13E4" in src else "★ 下界被删")

    # ---- U5: 模拟器检查仍存在 ----
    print("")
    print("U5 防改过头：模拟器检查仍存在:")
    rec("U5 仍含 16E4 与 Qn", ("16E4" in src) and ("Qn" in src),
        "OK" if ("16E4" in src and "Qn" in src) else "★ 模拟器检查被破坏")

    # ---- U6: 载荷本体未被改 ----
    #
    # ★★ 覆盖范围升级（A 路审核指出盲区，2026-09-30）：
    #   初版基线只含 `.js`/`.dylib`（103 项）—— **漏了 `.bin`（39 个，真正的原生载荷，
    #   `entry1_type0x0a.bin` 达 507,450 B）、`index.html`（161,042 B）、`payloads/manifest.json`**。
    #   若有人改 `.bin`，初版比对按【设计】就不会发现。
    #   ⇒ 改用全载荷基线 `_d0c5_payload_baseline_full.sha256`（144 项，已排除 group.html）。
    print("")
    print("U6 ★ 载荷本体不得被改（全载荷基线：.js/.dylib/.bin/.html/.json）:")
    baseline_file = os.path.join(
        IOS_ROOT + r"\_integration\_fix_work",
        "_d0c5_payload_baseline_full.sha256")
    if not os.path.isfile(baseline_file):
        rec("U6 载荷本体与基线一致", False,
            f"★ 全载荷基线不存在: {baseline_file}")
    else:
        base = {}
        for line in open(baseline_file, encoding="utf-8").read().splitlines():
            parts = line.split("  ", 1)
            if len(parts) == 2:
                base[parts[1].strip()] = parts[0].strip().lower()
        changed, missing = [], []
        for rel, want in base.items():
            p = os.path.join(ROOT, rel)
            if not os.path.isfile(p):
                missing.append(rel)
            elif sha256(p) != want:
                changed.append(rel)
        # 额外：列出基线未覆盖的新增可疑文件
        extras = []
        for dp, dn, fns in os.walk(ROOT):
            for fn in fns:
                if fn.endswith((".js", ".dylib", ".bin")):
                    rel = os.path.relpath(os.path.join(dp, fn), ROOT)
                    if rel not in base:
                        extras.append(rel)
        by_ext = {}
        for rel in base:
            e = os.path.splitext(rel)[1]
            by_ext[e] = by_ext.get(e, 0) + 1
        print(f"    基线 {len(base)} 项：{by_ext}")
        rec("U6 载荷本体逐位一致（含 .bin）",
            len(changed) == 0 and len(missing) == 0,
            f"改动 {len(changed)}；缺失 {len(missing)}"
            + (f"  改动: {changed[:5]}" if changed else "")
            + (f"  缺失: {missing[:5]}" if missing else ""))
        if extras:
            print(f"    （基线外新增 {len(extras)} 个 .js/.dylib/.bin，须人工确认）")
            for e in extras[:5]:
                print(f"      + {e}")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  coruna 已有上界告警且未改变放行行为、载荷本体未动")
    return 0


if __name__ == "__main__":
    sys.exit(main())
