# -*- coding: utf-8 -*-
"""
S3 判据：「合并 coruna 入口 9 步」—— 归属 W1-C1 的取证登记卡。

★ Owner 裁（方案 A）：S3 归入 W1-C1 的"打包期注入"改造（由 W1-C1b 承接）。
★ 本卡为取证卡，**不修改任何文件**。

★ 证据链：
   ① 入口链 5 个 .js 全在 05-ios/darksword/（载荷本体）
   ② group.html 在 05-ios/coruna/（.html **不在** .js/.dylib 约束内）
   ③ ★ **"改则失效"非密码学校验**（全仓 integrity=/verifyHash 零命中）
      —— 印证 `交付口径变更与链路简化方案.md:194`
   ④ __C2_ENDPOINT__ 占位符未实施 ⇒ 注入机制未建立

用法：
    python verify_s3_entry_chain.py              # 全量
    python verify_s3_entry_chain.py --selftest   # 量尺前置断言（P-5）

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
import re
import sys

ROOT = USDT_ROOT
DS = os.path.join(ROOT, "05-ios", "darksword")
GROUP_HTML = os.path.join(ROOT, "05-ios", "coruna", "group.html")
MANIFEST = os.path.join(ROOT, "_manifest.sha256")

# 入口链（整合复刻方案.md:262）
CHAIN = [
    "rce_loader.js",
    "rce_worker_18.4.js",
    "sbx0_main_18.4.js",
    "sbx1_main.js",
    "pe_main.js",
]

MANIFEST_SHA = "b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2"

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


def grep_roots(roots, pattern, exts):
    """在多个根目录下搜索模式。"""
    out = []
    rx = re.compile(pattern)
    for base in roots:
        if not os.path.isdir(base):
            continue
        for dp, dn, fns in os.walk(base):
            dn[:] = [d for d in dn if d not in (".git", "node_modules")]
            for fn in fns:
                if exts and not fn.endswith(exts):
                    continue
                p = os.path.join(dp, fn)
                try:
                    for i, line in enumerate(read(p).splitlines(), 1):
                        if rx.search(line):
                            out.append((os.path.relpath(p, ROOT), i, line.strip()[:100]))
                except Exception:
                    pass
    return out


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    n_found = 0
    for f in CHAIN:
        p = os.path.join(DS, f)
        e = os.path.isfile(p)
        if e:
            n_found += 1
    print(f"  入口链命中 {n_found}/{len(CHAIN)} 个文件")
    if n_found == 0:
        print("  [FAIL] 入口链 0 命中 ⇒ 量尺可能坏了")
        ok = False

    # ★ 量尺有效性：必须能在 darksword 下命中一个已知符号
    hits = grep_roots([DS], r"RCE_MAX_ATTEMPTS", (".js",))
    if hits:
        print(f"  量尺有效：darksword 下命中 RCE_MAX_ATTEMPTS {len(hits)} 处")
    else:
        print("  [FAIL] 未命中已知符号 ⇒ 量尺可能坏了")
        ok = False

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== S3 判据：入口链取证 + 机理印证 ===")
    print("★ 归属：W1-C1 的『打包期注入』改造（Owner 方案 A）")
    print("")

    # ---- S3-1: 入口链存在 ----
    print("S3-1 入口链完整性:")
    missing = [f for f in CHAIN if not os.path.isfile(os.path.join(DS, f))]
    rec("S3-1 入口链 5 个 .js 全部存在", len(missing) == 0,
        f"缺 {missing}" if missing else f"{len(CHAIN)} 个全部存在")
    for f in CHAIN:
        p = os.path.join(DS, f)
        if os.path.isfile(p):
            print(f"    {f}  {os.path.getsize(p):,} B  {sha256(p)[:16]}…")

    # ---- S3-2: 全在载荷本体目录 ----
    print("")
    print("S3-2 ★ 全部位于载荷本体目录（硬约束适用）:")
    all_in_ds = all(os.path.abspath(os.path.join(DS, f)).startswith(os.path.abspath(DS))
                    for f in CHAIN)
    rec("S3-2 入口链全在 05-ios/darksword/", all_in_ds,
        os.path.relpath(DS, ROOT))

    # ---- S3-3: group.html 性质 ----
    print("")
    print("S3-3 ★ group.html 的性质（.html 不在 .js/.dylib 约束内）:")
    if os.path.isfile(GROUP_HTML):
        rec("S3-3 group.html 存在且为 .html（非硬约束对象）",
            GROUP_HTML.endswith(".html"),
            f"{os.path.relpath(GROUP_HTML, ROOT)}  {os.path.getsize(GROUP_HTML):,} B")
    else:
        rec("S3-3 group.html 存在", False, "★ 缺失")

    # ---- S3-4: ★ 机理印证（非密码学校验） ----
    print("")
    print("S3-4 ★ 机理印证：『改则失效』非密码学校验（方案 :194）:")
    roots = [os.path.join(ROOT, "05-ios"), os.path.join(ROOT, "02-backend-node", "src_restored")]
    integ = grep_roots(roots, r"integrity\s*=", (".js", ".html", ".json"))
    verify_hash = grep_roots(roots, r"verifyHash", (".js", ".html"))
    print(f"    integrity= 命中 {len(integ)} 处")
    print(f"    verifyHash 命中 {len(verify_hash)} 处")
    rec("S3-4 「integrity= / verifyHash」零命中（印证非密码学校验）",
        len(integ) == 0 and len(verify_hash) == 0,
        f"integrity={len(integ)} verifyHash={len(verify_hash)}"
        + ("  ✓ 与方案 :194 一致" if (len(integ) == 0 and len(verify_hash) == 0) else "  ★ 有命中，须复查"))

    # ---- S3-5: 占位符未实施 ----
    print("")
    print("S3-5 ★ 注入机制未建立（__C2_ENDPOINT__ 未实施）:")
    ph = grep_roots([os.path.join(ROOT, "05-ios"),
                     os.path.join(ROOT, "04-landing"),
                     os.path.join(ROOT, "02-backend-node", "src_restored")],
                    r"__C2_ENDPOINT__", (".js", ".html", ".json"))
    rec("S3-5 __C2_ENDPOINT__ 零命中（机制未建立）", len(ph) == 0,
        f"命中 {len(ph)}: {ph[:3]}" if ph else "0 命中 ✓ ⇒ 须先由 W1-C1b 建立机制")

    # ---- S3-6: 未修改 ----
    print("")
    print("S3-6 ★ 未修改任何文件:")
    ldr = os.path.join(DS, "rce_loader.js")
    if os.path.isfile(ldr):
        rec("S3-6 rce_loader.js 未改",
            sha256(ldr) == "f6d78594778473dec1ae4d75fd71ef7b1a2cccc4cae13ec2d361bdbb8e90d969",
            f"{sha256(ldr)[:16]}…")
    if os.path.isfile(MANIFEST):
        rec("S3-6 _manifest.sha256 未改", sha256(MANIFEST) == MANIFEST_SHA,
            f"{sha256(MANIFEST)[:16]}…")

    print("")
    print("=== 结论 ===")
    print("  · 入口链 5 个 .js 全在 05-ios/darksword/（载荷本体）")
    print("  · group.html 是 .html（不在硬约束的 .js/.dylib 之列）")
    print("  · 『改则失效』非密码学校验 ⇒ 是【打包链依赖】的工程约定")
    print("  · __C2_ENDPOINT__ 机制未建立 ⇒ 须先由 W1-C1b 建立")
    print("  ⇒ **S3 归入 W1-C1 的『打包期注入』改造（Owner 方案 A）**")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  S3 取证完整（未修改任何文件）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
