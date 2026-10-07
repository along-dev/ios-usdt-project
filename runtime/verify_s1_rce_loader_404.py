# -*- coding: utf-8 -*-
"""
S1 判据：「消除 404 竞态（rce_loader.js:31）」—— 判定为【不适用】。

★ Owner 裁 (a)：结论登记卡，**不修改任何文件**。

★ 证据链（本判据把它们机械化为可核对的断言）：
   ① `:31` 附近是 `redirect()` → `.../assets/404.html`（代码事实）
   ② 该文件是【载荷本体】（位于 05-ios/darksword/）⇒ 硬约束「只读」适用
   ③ 它与 02-backend-node/templates/darksword/ 的副本【同哈希】
      ⇒ 改一份会造成 P-2
   ④ 上游报告 `09-docs/analysis/阶段1执行报告.md:51` 明确称其为「诱饵跳转」

用法：
    python verify_s1_rce_loader_404.py              # 全量
    python verify_s1_rce_loader_404.py --selftest   # 量尺前置断言（P-5）

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
PAYLOAD = os.path.join(ROOT, "05-ios", "darksword", "rce_loader.js")
COPY = os.path.join(ROOT, "02-backend-node", "templates", "darksword", "rce_loader.js")
REPORT = os.path.join(ROOT, "09-docs", "analysis", "阶段1执行报告.md")
MANIFEST = os.path.join(ROOT, "_manifest.sha256")

EXPECT_SHA = "f6d78594778473dec1ae4d75fd71ef7b1a2cccc4cae13ec2d361bdbb8e90d969"
EXPECT_BYTES = 8652
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


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    for p in (PAYLOAD, COPY, REPORT):
        e = os.path.isfile(p)
        print(f"  {'存在' if e else '[FAIL] 缺失'}: {os.path.relpath(p, ROOT)}")
        if not e:
            ok = False
    if ok:
        # ★ 量尺有效性：必须能定位到 "404.html" 这个字符串
        s = read(PAYLOAD)
        if "404.html" in s:
            print("  量尺有效：能在 rce_loader.js 中定位到 '404.html'")
        else:
            print("  [FAIL] 未找到 '404.html' ⇒ 量尺可能坏了")
            ok = False
    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== S1 判据：rce_loader.js:31 的「404」性质认定 ===")
    print("★ 结论：判定为【不适用】（Owner 裁 (a)）—— 无需实现、不修改任何文件")
    print("")

    # ---- S1-2: 该文件是载荷本体 ----
    print("S1-2 ★ 该文件位于载荷本体目录:")
    rec("S1-2 rce_loader.js 在 05-ios/darksword/ 下（硬约束适用）",
        os.path.abspath(PAYLOAD).startswith(os.path.abspath(os.path.join(ROOT, "05-ios"))),
        os.path.relpath(PAYLOAD, ROOT))

    # ---- S1-1: 含 redirect() 到 404.html ----
    print("")
    print("S1-1 ★ 代码事实（redirect() → 404.html）:")
    src = read(PAYLOAD)
    has_redirect = bool(re.search(r"function\s+redirect\s*\(", src))
    has_404 = "404.html" in src
    rec("S1-1 含 redirect() 函数", has_redirect, "已找到" if has_redirect else "★ 未找到")
    rec("S1-1 含 404.html 跳转", has_404, "已找到" if has_404 else "★ 未找到")
    # 打印实际代码行
    for i, line in enumerate(src.splitlines(), 1):
        if "404.html" in line or re.search(r"function\s+redirect", line):
            print(f"    :{i}  {line.strip()[:100]}")

    # ---- S1-3: 与副本同哈希 ----
    print("")
    print("S1-3 ★ 与 02-backend-node/templates 副本的一致性:")
    if os.path.isfile(COPY):
        hp, hc = sha256(PAYLOAD), sha256(COPY)
        rec("S1-3 载荷本体与副本同哈希（改一份会造成 P-2）", hp == hc,
            f"本体 {hp[:16]}… / 副本 {hc[:16]}…（{'相同' if hp == hc else '★ 不同' }）")
    else:
        rec("S1-3 副本存在", False, f"★ 缺失: {os.path.relpath(COPY, ROOT)}")

    # ---- S1-4: 上游报告称其为「诱饵跳转」 ----
    print("")
    print("S1-4 ★ 上游报告的定性:")
    rep = read(REPORT)
    m = re.search(r"^.*rce_loader\.js:31.*$", rep, re.M)
    line = m.group(0) if m else ""
    is_decoy = "诱饵跳转" in line
    rec("S1-4 报告 :51 称其为「诱饵跳转」", is_decoy,
        f"原文: {line.strip()[:110]}" if line else "★ 未找到该行")

    # ---- S1-5: 未修改任何文件 ----
    print("")
    print("S1-5 ★ 未修改任何文件:")
    rec("S1-5 载荷本体 sha256 未变", sha256(PAYLOAD) == EXPECT_SHA,
        f"{sha256(PAYLOAD)[:16]}…")
    rec("S1-5 载荷本体字节数未变", os.path.getsize(PAYLOAD) == EXPECT_BYTES,
        f"{os.path.getsize(PAYLOAD)} B")
    if os.path.isfile(MANIFEST):
        rec("S1-5 _manifest.sha256 未改", sha256(MANIFEST) == MANIFEST_SHA,
            f"{sha256(MANIFEST)[:16]}…")

    print("")
    print("=== 结论 ===")
    print("  · 「404.html 跳转」是载荷的【有意诱饵】（上游报告原文用词「诱饵跳转」）")
    print("  · 该文件是【载荷本体】⇒ 硬约束「只读（改则失效）」适用")
    print("  · 与副本同哈希 ⇒ 单独修改会造成 P-2")
    print("  ⇒ **S1 判定为「不适用」**（无需实现）")
    print("  ★ 若 Owner 能给出「竞态」的更具体定位 ⇒ 重开本卡")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  S1 判定为『不适用』的证据链完整（未修改任何文件）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
