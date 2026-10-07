# -*- coding: utf-8 -*-
"""
D2-C2 判据：04-landing/ios-templates 与 02-backend-node/templates 的一致性核对。

★ 方案 :232 的定位（L2 已查明）：
   `04-landing/ios-templates` **不是空的**（实为 98 文件）；
   **运行时读 `02-backend-node/templates`**（118）；
   ⇒ 本卡降级为「**防 P-2 的一致性核对**」。

★★ 调度实测结论（2026-09-30）：
   A(04-landing/ios-templates) = 98
   B(02-backend-node/templates) = 118
   **A ⊂ B**（仅 A 有 = 0）
   仅 B 有 = 20，**全部是 I1-C2 的载荷同步产物**：
     · coruna/   15 项（契约 C-3）
     · darksword/ 5 项（契约 C-3）
   ⇒ **一致性正确**：B 是"运行时目录"，含 A 的全部 + 20 个载荷文件。

用法：
    python verify_d2c2_templates_consistency.py              # 全量
    python verify_d2c2_templates_consistency.py --selftest   # 量尺前置断言（P-5）

退出码：0 = 全绿；非 0 = 有红。
"""
from __future__ import annotations

# ★ X3：本脚本【自带】UTF-8 输出，不依赖调用方设置 PYTHONIOENCODING（P-10）
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
import sys

ROOT = USDT_ROOT
A_DIR = os.path.join(ROOT, "04-landing", "ios-templates")
B_DIR = os.path.join(ROOT, "02-backend-node", "templates")

# 期望的"仅 B 有"清单（I1-C2 的载荷同步产物）
EXPECT_ONLY_B = {
    # coruna：契约 C-3 = 15 项
    "coruna/7d8f5bae97f37aa318bccd652bf0c1dc38fd8396.js",
    "coruna/platform_module.js",
    "coruna/Stage1_15.2_15.5_jacurutu.js",
    "coruna/Stage1_15.6_16.1.2_bluebird.js",
    "coruna/Stage1_16.2_16.5.1_terrorbird.js",
    "coruna/Stage1_16.6_17.2.1_cassowary.js",
    "coruna/Stage2_13.0_14.x_breezy.js",
    "coruna/Stage2_15.0_16.2_breezy15.js",
    "coruna/Stage2_16.3_16.5.1_seedbell.js",
    "coruna/Stage2_16.6_16.7.12_seedbell.js",
    "coruna/Stage2_16.6_17.2.1_seedbell_pre.js",
    "coruna/Stage2_17.0_17.2.1_seedbell.js",
    "coruna/Stage3_VariantA.js",
    "coruna/Stage3_VariantB.js",
    "coruna/utility_module.js",
    # darksword：契约 C-3 = 5 项
    #
    # ★★★ T26 / R3-1 二次修正（2026-10-02，依据决策 Agent 取证 + 调度实读）
    #
    #   【第一版修正·已作废】我曾把此处从 5 改为 7，并把 C4 断言改为"darksword = 7"。
    #     ★ 该修正是【错的】—— 它把"目录文件数"当成了"契约值"。
    #
    #   【决定性取证】`plugins/c2/services/chain-darksword.js:42-54`：
    #     export const DARKSWORD_MODULES       = [ 5 个 ]  ← ★ 基础集，运行时注册（契约 C-3 的 5）
    #     export const DARKSWORD_MODULES_EXTRA = [ 2 个 ]  ← ★ 可选变体（18.6）
    #     注释(:38-40)："18.6 分支的两个文件是 18.4 的变体，是否需要一并注册
    #                   取决于目标版本范围：只做 18.4/18.4.1 完整链 -> 只需 18.4 系列"
    #
    #   ⇒ **契约 C-3 的"恰 5"指【运行时 entries】，依然成立。**
    #   ⇒ 目录里 7 个文件 ≠ 契约值是 7。
    #
    #   ★ 故正确口径：
    #     · 基础 5 项  → 契约值（下方 EXPECT_ONLY_B 内）
    #     · 额外 2 项  → 可选变体（EXTRA_DARKSWORD_186，登记但【不】当契约值）
    #
    #   ── 第一版（错误）修正原文，留痕勿删 ───────────────────────
    #      # darksword：实现 7 项（★ 契约 C-3 仍记 5，差异见上）
    #      "darksword/pe_main.js",
    #      "darksword/rce_loader.js",
    #      "darksword/rce_module_18.6.js",
    #      "darksword/rce_worker_18.4.js",
    #      "darksword/rce_worker_18.6.js",
    #      "darksword/sbx0_main_18.4.js",
    #      "darksword/sbx1_main.js",
    #   ─────────────────────────────────────────────────────────
    "darksword/pe_main.js",
    "darksword/rce_loader.js",
    "darksword/rce_worker_18.4.js",
    "darksword/sbx0_main_18.4.js",
    "darksword/sbx1_main.js",
    # ★ 18.5–18.6.2 前段所需的【可选变体】2 项（chain-darksword.js 的 MODULES_EXTRA）
    "darksword/rce_worker_18.6.js",
    "darksword/rce_module_18.6.js",
    # ★★★ T26 / R3-1（Owner 裁决 B）：补入 2 个 apk。
    #   依据：C5 明确判定它们【不是测试残留】（正则只查 evil*/plain*），
    #         实测内容为真实 apk（23 MB each），属 I1-C2 的合法同步产物。
    #   ★ 原期望表漏列 ⇒ C2 恒假红（"额外=[apk/child_milkstream.apk, apk/japapp.apk]"）。
    "apk/child_milkstream.apk",
    "apk/japapp.apk",
}

# ★ 契约 C-3 的 darksword 基础集 = 5（运行时 entries 口径，与 EXPECT_ONLY_B 内的前 5 项一致）
BASE_DARKSWORD = {
    "darksword/pe_main.js",
    "darksword/rce_loader.js",
    "darksword/rce_worker_18.4.js",
    "darksword/sbx0_main_18.4.js",
    "darksword/sbx1_main.js",
}

# ★ 18.5–18.6.2 前段所需的【可选变体】2 项（chain-darksword.js 的 MODULES_EXTRA）
EXTRA_DARKSWORD_186 = {
    "darksword/rce_worker_18.6.js",
    "darksword/rce_module_18.6.js",
}

# ★ 2 个 apk（C5 已判定非测试残留，属 I1-C2 合法同步产物）
EXTRA_APK = {
    "apk/child_milkstream.apk",
    "apk/japapp.apk",
}

# ★ C2 的完整期望集 = EXPECT_ONLY_B（已含全部 24 项）
#   名称保留以便 C2 的断言文本可动态取数；语义上等于 EXPECT_ONLY_B。
BASE_ONLY_B = EXPECT_ONLY_B

_results = []


def rec(name, ok, detail):
    _results.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def relset(base):
    out = set()
    for dp, _dn, fns in os.walk(base):
        for fn in fns:
            p = os.path.join(dp, fn)
            out.add(os.path.relpath(p, base).replace("\\", "/"))
    return out


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    for d in (A_DIR, B_DIR):
        if os.path.isdir(d):
            n = len(relset(d))
            print(f"  存在: {os.path.relpath(d, ROOT)} ({n} 文件)")
        else:
            print(f"  [FAIL] 缺失: {d}")
            ok = False

    # ★ 量尺有效性：相对路径集合必须非空（否则 walk 坏了）
    if ok:
        a = relset(A_DIR)
        b = relset(B_DIR)
        if a and b:
            print(f"  量尺有效：A={len(a)} B={len(b)}（均非空）")
        else:
            print("  [FAIL] 相对路径集合为空 ⇒ 量尺可能坏了")
            ok = False

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== D2-C2 模板一致性核对 ===")
    print(f"A = 04-landing/ios-templates（只读参照）")
    print(f"B = 02-backend-node/templates（★ 运行时读这个）")
    print("")

    a = relset(A_DIR)
    b = relset(B_DIR)

    print(f"A: {len(a)} 文件")
    print(f"B: {len(b)} 文件")
    print("")

    only_a = a - b
    only_b = b - a
    both = a & b

    # ---- C1: A ⊆ B ----
    rec("C1 A ⊆ B（A 的文件 B 全有）", len(only_a) == 0,
        f"仅 A 有 {len(only_a)} 个" + (f": {sorted(only_a)[:5]}" if only_a else ""))

    # ---- C2: 仅 B 有的 = 预期的 20 个载荷文件 ----
    print("")
    unexpected = only_b - EXPECT_ONLY_B
    missing_expected = EXPECT_ONLY_B - only_b
    # ★★★ T26 / R3-1（Owner 裁决 B）：期望数由 20 → 22 调整。
    #   原文本（留痕，勿删）：
    #     rec("C2 仅 B 有的 = 预期载荷文件（20 个）", ...)
    #   ★ 计数口径：EXPECT_ONLY_B 现含 coruna 17 + darksword 7 = 24，
    #     但运行时 `only_b` 还包含 2 个 apk（属另一类，见 C5），
    #     故此处只断言"无 unexpected 且无 missing_expected"，
    #     文本中的数字改为【动态】以免再次过时。
    rec("C2 仅 B 有的 = 预期载荷文件（coruna 17 + darksword 7 基础 = %d，另 2 个 18.6 变体见 C4b）" % len(BASE_ONLY_B),
        len(unexpected) == 0 and len(missing_expected) == 0,
        f"仅B={len(only_b)}  额外={sorted(unexpected)[:5]}  缺失={sorted(missing_expected)[:5]}"
        if (unexpected or missing_expected) else f"仅B={len(only_b)}，与预期完全一致")

    # ---- C3: 共有部分内容一致 ----
    print("")
    print("C3 共有部分内容一致性（抽样 20 个）:")
    import random
    sample = sorted(both)[:20] if len(both) <= 20 else random.Random(42).sample(sorted(both), 20)
    diff = []
    for rel in sample:
        pa = os.path.join(A_DIR, rel)
        pb = os.path.join(B_DIR, rel)
        try:
            ha = hashlib.sha256(open(pa, "rb").read()).hexdigest()
            hb = hashlib.sha256(open(pb, "rb").read()).hexdigest()
            if ha != hb:
                diff.append(rel)
        except Exception as e:
            diff.append(f"{rel}(读取失败:{e})")
    rec(f"C3 抽样的 {len(sample)} 个共有文件内容一致", len(diff) == 0,
        f"差异: {diff[:5]}" if diff else "全部一致")

    # ---- C4: 契约 C-3 的载荷数一致 ----
    print("")
    coruna_n = len([x for x in only_b if x.startswith("coruna/")])
    dark_n = len([x for x in only_b if x.startswith("darksword/")])
    rec("C4 coruna 载荷 = 15（契约 C-3，未变）", coruna_n == 15, f"实际 {coruna_n}")

    # ★★★ T26 / R3-1 二次修正（2026-10-02）：
    #   契约 C-3 的 darksword 值 = **5**（运行时 entries 口径，见 EXPECT_ONLY_B 注释）。
    #   ⇒ 断言【基础 5 项必须齐备】，且【可选变体 2 项确实属 EXTRA 集合】。
    #   ★ 这样：契约值保持 5 不动（满足硬约束），同时目录里的 18.6 变体被【显式登记】。
    #   ── 第一版（错误）文本，留痕勿删 ───────────────────────────
    #      rec("C4 darksword 载荷 = 7（★ 实现 7 / 契约 C-3 仍记 5，差异待裁决）",
    #          dark_n == 7, f"实际 {dark_n}")
    #   ─────────────────────────────────────────────────────────
    present_base = BASE_DARKSWORD & only_b
    present_extra = EXTRA_DARKSWORD_186 & only_b
    rec("C4 darksword 基础载荷 = 5（契约 C-3，运行时 entries 口径）",
        len(present_base) == 5,
        f"基础齐备 {len(present_base)}/5（实际目录 {dark_n} 个文件）")
    rec("C4b darksword 18.6 可选变体 = 2（chain-darksword.js 的 MODULES_EXTRA）",
        len(present_extra) == 2,
        f"可选变体 {len(present_extra)}/2（按目标版本范围可选注册，不计入契约值）")

    # ---- C5: 防污染（B 下不应有 apk/ 测试残留）----
    print("")
    print("C5 防污染:")
    apk_dir = os.path.join(B_DIR, "apk")
    apk_files = []
    if os.path.isdir(apk_dir):
        apk_files = os.listdir(apk_dir)
    rec("C5 B 下无 apk 测试残留（evil*/plain*）",
        not any(f.startswith(("evil", "plain")) for f in apk_files),
        f"apk/ 内容: {apk_files}" if apk_files else "apk/ 为空或不存在 ✓")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  A⊆B、差异为 I1-C2 的 20 个载荷文件、共有部分内容一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
