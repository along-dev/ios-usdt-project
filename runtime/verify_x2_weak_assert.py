# -*- coding: utf-8 -*-
"""
X2 判据：修判据弱断言（`!= 404`、硬编码 `True`）。

★ 方案 :261 定档 R2。

★ 调度取证（56 个 verify_*.py 全扫，实测 5 处弱断言）：
   | # | 文件 | 行 | 弱断言 |
   |---|---|---|---|
   | 1 | verify_d1c5b_admin_data.py | 283 | `st7 != 404`（过宽）|
   | 2 | verify_d1c5b_admin_data.py | 261 | `rec(..., True, ...)`（硬编码）|
   | 3 | verify_d2c4_apk_delivery.py | 236 | `rec(..., True, ...)` |
   | 4 | verify_d2c4_apk_delivery.py | 238 | `rec(..., True, ...)` |
   | 5 | verify_d2c5_filzaslop_static.py | 238 | `rec(..., True, ...)` |

★ 调度已实测 logout 的确切期望值 = **302**（带/不带 token 均是）。

用法：
    python verify_x2_weak_assert.py              # 全量
    python verify_x2_weak_assert.py --selftest   # 量尺前置断言（P-5）

退出码：0 = 全绿；非 0 = 有红。
"""
from __future__ import annotations

import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import argparse
import glob
import hashlib
import io
import os
import re
import sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

D = IOS_ROOT + r"\_integration\_fix_work"
MANIFEST = USDT_ROOT + r"\_manifest.sha256"

# ★ 本卡涉及的 3 个脚本
TARGETS = [
    "verify_d1c5b_admin_data.py",
    "verify_d2c4_apk_delivery.py",
    "verify_d2c5_filzaslop_static.py",
]

MANIFEST_SHA = "b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2"

# ★ 弱断言模式（排除本卡判据自身）
WEAK = [
    (r"!=\s*404", "`!= 404`（过宽：401/500 也算过）"),
    (r"!==\s*404", "`!== 404`（过宽）"),
    (r"in\s*\(\s*200\s*,\s*404\s*\)", "`in (200, 404)`（过宽）"),
]

_results = []


def rec(name, ok, detail):
    _results.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def read(p):
    return io.open(p, encoding="utf-8", errors="replace").read()


def scan_weak(exclude_self=True):
    """返回 [(文件, 行, 内容, 模式描述)]。"""
    out = []
    for p in sorted(glob.glob(os.path.join(D, "verify_*.py"))):
        base = os.path.basename(p)
        if exclude_self and base == "verify_x2_weak_assert.py":
            continue
        try:
            lines = read(p).splitlines()
        except Exception:
            continue
        for i, l in enumerate(lines, 1):
            # 跳过注释行（避免把"说明文字"误判为断言）
            st = l.strip()
            if st.startswith("#"):
                continue
            for pat, desc in WEAK:
                if re.search(pat, l):
                    out.append((base, i, st[:100], desc))
    return out


def scan_hardcoded_true():
    """找无条件 rec(..., True, ...)（排除本卡判据）。"""
    out = []
    for p in sorted(glob.glob(os.path.join(D, "verify_*.py"))):
        base = os.path.basename(p)
        if base == "verify_x2_weak_assert.py":
            continue
        try:
            lines = read(p).splitlines()
        except Exception:
            continue
        for i, l in enumerate(lines, 1):
            st = l.strip()
            if st.startswith("#"):
                continue
            # rec("...", True, ...  —— 第二参数为字面量 True
            if re.search(r"rec\([^,]*,\s*True\s*,", l):
                out.append((base, i, st[:110]))
    return out


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    n = len(glob.glob(os.path.join(D, "verify_*.py")))
    print(f"  verify_*.py 共 {n} 个")
    if n == 0:
        print("  [FAIL] 0 个脚本 ⇒ 量尺坏了")
        ok = False
    for t in TARGETS:
        p = os.path.join(D, t)
        e = os.path.isfile(p)
        print(f"  {'存在' if e else '[FAIL] 缺失'}  {t}")
        if not e:
            ok = False
    # ★ 量尺有效性：必须能检出一个已知的弱断言样本
    sample = 'rec("x", st7 != 404, f"HTTP={st7}")'
    if re.search(r"!=\s*404", sample):
        print("  量尺有效：可识别 `!= 404` 模式")
    else:
        print("  [FAIL] 模式失效")
        ok = False
    print(f"  当前弱断言命中：{len(scan_weak())} 处")
    print(f"  当前硬编码 True：{len(scan_hardcoded_true())} 处")
    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== X2 判据：修判据弱断言 ===")
    print("")

    # ---- Z1: 无过宽断言 ----
    print("Z1 ★ 过宽断言（`!= 404` 类）:")
    weak = scan_weak()
    rec("Z1 不存在过宽断言", len(weak) == 0,
        f"★ 仍有 {len(weak)} 处: {[(w[0], w[1]) for w in weak]}" if weak
        else "0 处 ✓")
    for f, i, l, d in weak:
        print(f"    {f}:{i}  {l}   [{d}]")

    # ---- Z2: 无无条件硬编码 True ----
    print("")
    print("Z2 ★ 无条件 `rec(..., True, ...)`:")
    hard = scan_hardcoded_true()
    rec("Z2 不存在无条件硬编码 True", len(hard) == 0,
        f"★ 仍有 {len(hard)} 处: {[(h[0], h[1]) for h in hard]}" if hard
        else "0 处 ✓")
    for f, i, l in hard:
        print(f"    {f}:{i}  {l}")

    # ---- Z3: SKIP 标注存在（"APK < 2 无法判序" 类）----
    #
    # ★★ 修正（2026-09-30，执行者指出 + 调度确认）：
    #   初版用 `re.search(r"D5.{0,600}", s, re.S)` —— 【固定 600 字符窗口】，
    #   而 D5 的 `[SKIP]` 落在首个 `D5` 之后 **763 字符**处 ⇒ **恒红**（量尺 bug）。
    #   ⇒ 改为【按缩进块取段】：从含 D5 的行起，取到**缩进回退**为止
    #     （即整个 D5 分支），窗口随代码长度自适应。
    print("")
    print("Z3 ★ `apk/list 排序` 类的 SKIP 标注（★ 按缩进块取段，非固定窗口）:")
    p1 = os.path.join(D, "verify_d1c5b_admin_data.py")
    if os.path.isfile(p1):
        src_lines = read(p1).splitlines()
        seg_lines = []
        started = False
        base_indent = None
        for l in src_lines:
            if not started:
                if "D5" in l:
                    started = True
                    base_indent = len(l) - len(l.lstrip())
                    seg_lines.append(l)
                continue
            # 已进入 D5 段：缩进回退到 base 以下 ⇒ 段结束
            if l.strip() and (len(l) - len(l.lstrip())) < base_indent:
                break
            seg_lines.append(l)
        seg = "\n".join(seg_lines)
        print(f"    （D5 段长度 {len(seg)} 字符，覆盖 {len(seg_lines)} 行）")
        has_skip = ("[SKIP]" in seg) or ("SKIP" in seg and "不等于 PASS" in seg)
        has_true = bool(re.search(r"rec\([^,]*D5[^,]*,\s*True", seg))
        rec("Z3 D5 已改为 SKIP 标注（非无条件 True）", has_skip and not has_true,
            f"含 SKIP={has_skip} 仍无条件 True={has_true}")

    # ---- Z4: 改造后的判据仍能正常工作 ----
    print("")
    print("Z4 ★ 改造后的判据仍能跑（EXIT 符合预期）:")
    print("    （本项只做【静态存在性】检查；真跑由执行者提供证据）")
    for t in TARGETS:
        p = os.path.join(D, t)
        if os.path.isfile(p):
            s = read(p)
            has_main = "__main__" in s
            rec(f"Z4 {t} 结构完整（含 __main__）", has_main, "✓" if has_main else "★ 缺失")

    # ---- Z5: 未改产物 ----
    print("")
    print("Z5 ★ 未改任何产物代码:")
    checks = [
        (USDT_ROOT + r"\02-backend-node\src_restored\plugins\api\routes\landing.js",
         "3208c207bf423c8d99577c0508e9b6cc809f471dcd590ee0e96b87906e7de632"),
        (USDT_ROOT + r"\03-web-admin\static\admin_dashboard.html",
         "9bad2f7f3a047a9fb988ca9f0c022df2db61b05ac2d548c74449eecdd6b85ce5"),
    ]
    for p, want in checks:
        if os.path.isfile(p):
            cur = sha256(p)
            rec(f"Z5 {os.path.basename(p)} 未改", cur == want, f"{cur[:16]}…")

    # ---- Z6: 守护 ----
    print("")
    if os.path.isfile(MANIFEST):
        rec("Z6 _manifest.sha256 未改", sha256(MANIFEST) == MANIFEST_SHA,
            f"{sha256(MANIFEST)[:16]}…")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  弱断言已消除、判据结构完整、产物未改")
    return 0


if __name__ == "__main__":
    sys.exit(main())
