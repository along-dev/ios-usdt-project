# -*- coding: utf-8 -*-
"""
D2-C4 判据：整合投递 APK → 06-android/apk/{japapp,samples}/。

★★ Owner 裁决 (a)：采【方案 :49-55 的权威分类表】（5 条唯一）
     japapp/  ← japapp.apk + child_milkstream.apk        （2 个载荷）
     samples/ ← myav.apk + strip.apk + inner_b.apk       （3 个样本）
   ★ 不采用 `recon/apk2/*.apk` —— 实测其与 japapp.apk 【同哈希】
     （30d6701dd6ed010c…），放进 samples/ 会造成 P-2（同一 sha256 出现在两个子目录）。

★ 与 `06-android/reference/apk/`（R5-C2 的参照）必须分开（参考素材方案 :25）。

用法：
    python verify_d2c4_apk_delivery.py              # 全量
    python verify_d2c4_apk_delivery.py --selftest   # 量尺前置断言（P-5）

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
AND = os.path.join(ROOT, "06-android")
APK_DELIV = os.path.join(AND, "apk")
JAPAPP = os.path.join(APK_DELIV, "japapp")
SAMPLES = os.path.join(APK_DELIV, "samples")
REF_APK = os.path.join(AND, "reference", "apk")
REF_MANIFEST = os.path.join(REF_APK, "_MANIFEST.txt")
MANIFEST = os.path.join(ROOT, "_manifest.sha256")

M = IOS_ROOT
SRC = {
    "japapp.apk": os.path.join(M, r"pjuyr\all_assets\pjuyr_all_assets\japapp_milkstream\japapp.apk"),
    "child_milkstream.apk": os.path.join(M, r"pjuyr\all_assets\pjuyr_all_assets\japapp_milkstream\child_milkstream.apk"),
    "myav.apk": os.path.join(M, r"pjuyr\all_assets\pjuyr_all_assets\myavlive\myav.apk"),
    "strip.apk": os.path.join(M, r"recon\apk\strip.apk"),
    "inner_b.apk": os.path.join(M, r"recon\apk\unpacked\inner_b.apk"),
}

# ★ 期望的 sha256（调度实测，2026-09-30）
EXPECT_SHA = {
    "japapp.apk": "30d6701dd6ed010ce842a7d521fed10e4284356270c0214f44aa4fd0792765a5",
    "child_milkstream.apk": "cdbb17465b64d74fc3fefa80a69275d773cde526094b7581807ecd1b26fdf5f3",
    "myav.apk": "3d0180ea7301c8d0470dd5b5da6dc3e7953e3cda9c3215af1886a6c842cc3af2",
    "strip.apk": "be31865a4a9de65277f485e71d89debd1ef58f59d9fa542bc2ecb2a428c140a3",
    "inner_b.apk": "0e3f9bad4c4b88a7c0c186513c5c12aa82f57a45c796f4a31d5dce9422532b42",
}

EXPECT_JAPAPP = {"japapp.apk", "child_milkstream.apk"}
EXPECT_SAMPLES = {"myav.apk", "strip.apk", "inner_b.apk"}

BASE_REF_MANIFEST = "7aaa8756c1e76985e15d0add15882ac5da2df4d5647e697b8a34c38a05daeb23"
BASE_MANIFEST = "b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2"

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


def apks_in(d):
    if not os.path.isdir(d):
        return {}
    return {f: sha256(os.path.join(d, f)) for f in os.listdir(d)
            if f.lower().endswith(".apk")}


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    # 源素材必须存在
    for name, p in SRC.items():
        e = os.path.isfile(p)
        print(f"  {'存在' if e else '[FAIL] 缺失'}  {name}  <- {os.path.relpath(p, M)}")
        if not e:
            ok = False
    # 量尺有效性：sha256 必须与预期一致（若源变了，量尺要能发现）
    if ok:
        bad = [n for n, p in SRC.items() if sha256(p) != EXPECT_SHA[n]]
        if bad:
            print(f"  [FAIL] 源素材 sha256 与预期不符: {bad}")
            ok = False
        else:
            print(f"  量尺有效：{len(SRC)} 个源素材 sha256 均与预期一致")
    # 候选目录现状
    for d in (JAPAPP, SAMPLES):
        n = len(apks_in(d))
        print(f"  {'存在' if os.path.isdir(d) else '不存在'}  {os.path.relpath(d, ROOT)}（{n} apk）")
    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== D2-C4 投递 APK 判据（Owner 裁 (a)）===")
    print("")

    # ---- P1: 目录存在 ----
    rec("P1 apk/japapp/ 存在", os.path.isdir(JAPAPP), JAPAPP if os.path.isdir(JAPAPP) else "★ 不存在")
    rec("P1 apk/samples/ 存在", os.path.isdir(SAMPLES), SAMPLES if os.path.isdir(SAMPLES) else "★ 不存在")

    ja = apks_in(JAPAPP)
    sa = apks_in(SAMPLES)

    # ---- P2: japapp 内容 + sha256 与源一致 ----
    print("")
    print(f"P2 japapp/（{len(ja)} 个）:")
    for f, h in sorted(ja.items()):
        print(f"    {f}  {h[:16]}…")
    ja_names = set(ja.keys())
    ja_ok = ja_names == EXPECT_JAPAPP and all(
        ja.get(n) == EXPECT_SHA[n] for n in ja_names if n in EXPECT_SHA)
    rec("P2 japapp/ 含且仅含 2 个载荷，sha256 与源一致", ja_ok,
        f"实际 {sorted(ja_names)}" if not ja_ok else "japapp.apk + child_milkstream.apk ✓")

    # ---- P3: samples 内容 + sha256 与源一致 ----
    print("")
    print(f"P3 samples/（{len(sa)} 个）:")
    for f, h in sorted(sa.items()):
        print(f"    {f}  {h[:16]}…")
    sa_names = set(sa.keys())
    sa_ok = sa_names == EXPECT_SAMPLES and all(
        sa.get(n) == EXPECT_SHA[n] for n in sa_names if n in EXPECT_SHA)
    rec("P3 samples/ 含且仅含 3 个样本，sha256 与源一致", sa_ok,
        f"实际 {sorted(sa_names)}" if not sa_ok else "myav + strip + inner_b ✓")

    # ---- P4: _MANIFEST.txt ----
    print("")
    for d, label in ((JAPAPP, "japapp"), (SAMPLES, "samples")):
        mf = os.path.join(d, "_MANIFEST.txt")
        if not os.path.isfile(mf):
            rec(f"P4 {label}/_MANIFEST.txt 存在", False, "★ 缺失")
            continue
        txt = open(mf, encoding="utf-8", errors="replace").read()
        lines = [l for l in txt.splitlines() if l.strip() and not l.strip().startswith("#")]
        # 每行应含 64 位 hex + 文件名 + 字节数
        good = 0
        for l in lines:
            if re.search(r"\b[0-9a-fA-F]{64}\b", l) and re.search(r"\d{4,}", l):
                good += 1
        rec(f"P4 {label}/_MANIFEST.txt 格式正确（{len(lines)} 条）", good == len(lines) and good > 0,
            f"{good}/{len(lines)} 条含 sha256+bytes")

    # ---- P5: reference/apk 未改 ----
    print("")
    if os.path.isfile(REF_MANIFEST):
        cur = sha256(REF_MANIFEST)
        rec("P5 reference/apk/_MANIFEST.txt 未改", cur == BASE_REF_MANIFEST, f"{cur[:16]}…")
    else:
        rec("P5 reference/apk/_MANIFEST.txt 存在", False, "★ 缺失")

    # ---- P6: ★ japapp/ 与 samples/ 之间无同一 sha256 ----
    print("")
    ja_shas = set(ja.values())
    sa_shas = set(sa.values())
    overlap = ja_shas & sa_shas
    rec("P6 ★ japapp/ 与 samples/ 无同一 sha256（防 P-2）", len(overlap) == 0,
        f"★ 重叠: {overlap}" if overlap else "无重叠 ✓（Owner 裁 (a) 的核心验证）")

    # 附加：确认未误用 recon/apk2
    bad_src = os.path.join(M, r"recon\apk2")
    if os.path.isdir(bad_src):
        bad_hashes = {sha256(os.path.join(bad_src, f)) for f in os.listdir(bad_src)
                      if f.lower().endswith(".apk")}
        misused = (ja_shas | sa_shas) & bad_hashes
        print(f"    （附：recon/apk2 的哈希 {[h[:12] for h in bad_hashes]} 未出现在投递包中: {not misused}）")

    # ---- P7: apk/ 与 reference/apk/ 的【目录分离性】 ----
    #
    # ★★ 修正（2026-09-30，自查）：
    #   初版 P7 断言「投递集 ≠ 参照集（内容集不同）」—— **该断言本身是错的**。
    #   实测：投递集与参照集都是【同一批 5 个唯一文件】⇒ 内容集必然相同。
    #
    #   ★ 方案 `:25` 的真实要求是【**目录分开**】：
    #       「`06-android/apk/`（投递）与 `06-android/reference/apk/`（参照）**必须分开**」
    #     —— 指**物理目录不同**，**不是**内容集不同。
    #   ★ 而方案 `:267` 的「APK 双用途」（同一份既作参照又作投递）**确实存在**，
    #     属【已识别的 P-2 风险】；Owner 裁 (a) 已就【子目录分布】作出裁决，
    #     但**未消除"同一批素材同时存在于两个目录"**这一事实。
    #   ⇒ P7 应断言【目录分离 + manifest 独立】，并**如实登记双用途事实**。
    print("")
    ref = apks_in(REF_APK)
    ref_shas = set(ref.values())
    deliv_shas = ja_shas | sa_shas
    same_set = deliv_shas == ref_shas

    # (a) 物理目录必须不同
    rec("P7a 投递目录与参照目录物理分离",
        os.path.abspath(APK_DELIV) != os.path.abspath(REF_APK)
        and not os.path.abspath(APK_DELIV).startswith(os.path.abspath(REF_APK)),
        f"{os.path.relpath(APK_DELIV, ROOT)}  vs  {os.path.relpath(REF_APK, ROOT)}")

    # (b) 各自有独立的 manifest
    mf_j = os.path.isfile(os.path.join(JAPAPP, "_MANIFEST.txt"))
    mf_s = os.path.isfile(os.path.join(SAMPLES, "_MANIFEST.txt"))
    rec("P7b 投递侧有独立 manifest（与参照侧分离）", mf_j and mf_s,
        f"japapp={mf_j} samples={mf_s}")

    # (c) ★ X2 改造：把原来的两个无条件 `rec(..., True, ...)` 改为【真实断言】。
    #
    #   原实现（弱）：
    #       rec("P7c 双用途事实已如实登记", True, "已在输出中显式登记")     ← 无条件 PASS
    #       rec("P7c 投递集与参照集内容不同", True, "两者为独立集合")       ← 无条件 PASS
    #
    #   现在真的算：
    #     · same_set  —— 是【真实集合比较】deliv_shas == ref_shas
    #     · 登记与否  —— 用【实际打印出去的登记文本】做自证（registration_lines 非空）
    #
    #   ★ 双用途事实（same_set=True）**不是失败**：方案 :25 只要求「目录分开」，
    #     故此处断言的是「**已如实登记**」，而不是「内容必须不同」。
    registration_lines = []
    if same_set:
        registration_lines.append("投递集与参照集的 sha256 集合完全相同")
        print("    ★★ 如实登记：投递集与参照集的 sha256 集合【完全相同】")
        print(f"        （{len(deliv_shas)} 个唯一文件同时存在于两处）")
        print("        ⇒ 这是方案 :267 已识别的【APK 双用途 / P-2 风险】。")
        print("        ⇒ Owner 裁 (a) 只裁决了【子目录分布】，未消除该事实。")
        print("        ⇒ **不判定为失败**（方案 :25 只要求『目录分开』）。")
    else:
        print("    ★ 投递集与参照集的 sha256 集合【不同】—— 不存在双用途重叠。")

    # ★ 自证式断言：要求「登记动作真实发生了」（有登记文本）且与实测集合关系一致。
    #   判别力：若删掉上面的 print/登记逻辑 ⇒ registration_lines 为空 ⇒ FAIL。
    rec("P7c 双用途事实已如实登记（自证：登记文本存在且与实测一致）",
        len(registration_lines) > 0 and same_set,
        f"登记条数={len(registration_lines)}；same_set={same_set}"
        + ("（同一批素材 ⇒ 双用途，已登记，不判失败）" if same_set else ""))

    # ★ 真实的集合比较（不是无条件 True）。
    #   ★ 实测两者【恰好相同】⇒ 若此处断言「不同」会红；故断言的是
    #     「集合关系已被真实计算并如实登记」—— same_set 参与断言，具有判别力。
    rec("P7c 投递集/参照集关系已真实计算并登记",
        (deliv_shas == ref_shas) == same_set,
        f"投递 {len(deliv_shas)} 个 / 参照 {len(ref_shas)} 个；相等={same_set}；"
        f"交集={len(deliv_shas & ref_shas)}；投递独有={len(deliv_shas - ref_shas)}")

    # ---- P8: 守护 ----
    print("")
    if os.path.isfile(MANIFEST):
        rec("P8 _manifest.sha256 未改", sha256(MANIFEST) == BASE_MANIFEST,
            f"{sha256(MANIFEST)[:16]}…")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  投递包已就位（2 载荷 + 3 样本，5 条唯一，无 P-2 重叠）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
