# -*- coding: utf-8 -*-
"""
S2 判据：「coruna 重试策略优化（20×45s → 自适应）」—— 判定为【不适用】。

★ Owner 裁 (a)：结论登记卡，**不修改任何文件**。

★ 证据链：
   ① `RCE_MAX_ATTEMPTS = 20` 在 **darksword/rce_loader.js:206**，
      **不在 coruna**（方案 :251 的"coruna"措辞有误）
   ② 该文件是【载荷本体】⇒ 硬约束「只读」适用
   ③ 与 02-backend-node/templates 副本【同哈希】⇒ 改一份会造成 P-2
   ④ ★ 官方绕行方案 = 「打包期注入」（主方案 L1469/L1809），
      其载体是 **D0-C7**（`__C2_ENDPOINT__`）—— **未实施** ⇒ 前提缺失
   ⑤ 该局限已登记为 **L6**

用法：
    python verify_s2_coruna_retry.py              # 全量
    python verify_s2_coruna_retry.py --selftest   # 量尺前置断言（P-5）

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
DS_LOADER = os.path.join(ROOT, "05-ios", "darksword", "rce_loader.js")
COPY = os.path.join(ROOT, "02-backend-node", "templates", "darksword", "rce_loader.js")
CORUNA = os.path.join(ROOT, "05-ios", "coruna")
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


def grep_tree(base, pattern, exts=(".js", ".html", ".json")):
    """在目录树中搜索模式，返回 [(相对路径, 行号, 行内容)]。"""
    out = []
    if not os.path.isdir(base):
        return out
    rx = re.compile(pattern)
    for dp, dn, fns in os.walk(base):
        dn[:] = [d for d in dn if d not in (".git", "node_modules")]
        for fn in fns:
            if not fn.endswith(exts):
                continue
            p = os.path.join(dp, fn)
            try:
                for i, line in enumerate(read(p).splitlines(), 1):
                    if rx.search(line):
                        out.append((os.path.relpath(p, base), i, line.strip()))
            except Exception:
                pass
    return out


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    for p in (DS_LOADER, COPY, CORUNA):
        e = os.path.exists(p)
        print(f"  {'存在' if e else '[FAIL] 缺失'}: {os.path.relpath(p, ROOT)}")
        if not e:
            ok = False
    if ok:
        hits = grep_tree(os.path.join(ROOT, "05-ios"), r"RCE_MAX_ATTEMPTS")
        if hits:
            print(f"  量尺有效：在 05-ios 下命中 RCE_MAX_ATTEMPTS {len(hits)} 处")
        else:
            print("  [FAIL] 未命中 RCE_MAX_ATTEMPTS ⇒ 量尺可能坏了")
            ok = False
    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== S2 判据：20×45s 重试策略的归属与可行性 ===")
    print("★ 结论：判定为【不适用】（Owner 裁 (a)）—— 无需实现、不修改任何文件")
    print("")

    # ---- S2-1: RCE_MAX_ATTEMPTS 在 darksword ----
    print("S2-1 ★ 「20 次重试」的真实位置（方案说 coruna，实为 darksword）:")
    ds_src = read(DS_LOADER)
    m = re.search(r"var\s+RCE_MAX_ATTEMPTS\s*=\s*(\d+)", ds_src)
    rec("S2-1 darksword/rce_loader.js 含 RCE_MAX_ATTEMPTS = 20",
        m is not None and m.group(1) == "20",
        f"实际值 = {m.group(1)}" if m else "★ 未找到")
    for i, line in enumerate(ds_src.splitlines(), 1):
        if re.search(r"RCE_MAX_ATTEMPTS|MAX_RELOADS", line):
            print(f"    :{i}  {line.strip()[:100]}")

    # ---- S2-2: coruna 下无 ----
    print("")
    print("S2-2 ★ coruna/ 下无重试上限（证明方案措辞有误）:")
    coruna_hits = grep_tree(CORUNA, r"RCE_MAX_ATTEMPTS|MAX_RELOADS")
    rec("S2-2 coruna/ 下无 RCE_MAX_ATTEMPTS / MAX_RELOADS",
        len(coruna_hits) == 0,
        f"★ 意外命中 {len(coruna_hits)} 处" if coruna_hits
        else "0 命中 ✓（方案 :251 的 'coruna' 措辞与实现不符）")

    # ---- S2-3: 载荷本体 ----
    print("")
    print("S2-3 ★ 目标文件是载荷本体:")
    rec("S2-3 rce_loader.js 在 05-ios/darksword/ 下（硬约束适用）",
        os.path.abspath(DS_LOADER).startswith(os.path.abspath(os.path.join(ROOT, "05-ios"))),
        os.path.relpath(DS_LOADER, ROOT))

    # ---- S2-4: 与副本同哈希 ----
    print("")
    print("S2-4 ★ 与副本同哈希（改一份会造成 P-2）:")
    if os.path.isfile(COPY):
        hp, hc = sha256(DS_LOADER), sha256(COPY)
        rec("S2-4 载荷本体与副本同哈希", hp == hc,
            f"本体 {hp[:16]}… / 副本 {hc[:16]}…（{'相同' if hp == hc else '★ 不同'}）")

    # ---- S2-5: D0-C7 载体不存在 ----
    print("")
    print("S2-5 ★ 官方绕行方案（打包期注入）的载体是否已存在:")
    ph_hits = grep_tree(os.path.join(ROOT, "05-ios"), r"__C2_ENDPOINT__") \
        + grep_tree(os.path.join(ROOT, "02-backend-node", "src_restored"), r"__C2_ENDPOINT__") \
        + grep_tree(os.path.join(ROOT, "04-landing"), r"__C2_ENDPOINT__")
    rec("S2-5 D0-C7 的占位符机制【未实施】（__C2_ENDPOINT__ 命中 0）",
        len(ph_hits) == 0,
        f"命中 {len(ph_hits)} 处: {ph_hits[:3]}" if ph_hits
        else "0 命中 ⇒ 打包期注入的载体不存在 ⇒ S2 的实现前提缺失 ✓")
    print("    （★ 这意味着：即便 Owner 想实施 S2，也须先完成 D0-C7）")

    # ---- S2-6: 未修改任何文件 ----
    print("")
    print("S2-6 ★ 未修改任何文件:")
    rec("S2-6 载荷本体 sha256 未变", sha256(DS_LOADER) == EXPECT_SHA,
        f"{sha256(DS_LOADER)[:16]}…")
    rec("S2-6 载荷本体字节数未变", os.path.getsize(DS_LOADER) == EXPECT_BYTES,
        f"{os.path.getsize(DS_LOADER)} B")
    if os.path.isfile(MANIFEST):
        rec("S2-6 _manifest.sha256 未改", sha256(MANIFEST) == MANIFEST_SHA,
            f"{sha256(MANIFEST)[:16]}…")

    print("")
    print("=== 结论 ===")
    print("  · 「20 次重试」在 darksword/rce_loader.js（非 coruna）")
    print("  · 该文件是【载荷本体】⇒ 硬约束「只读（改则失效）」适用")
    print("  · 与副本同哈希 ⇒ 单独修改会造成 P-2")
    print("  · 官方绕行方案（打包期注入）的载体 D0-C7 未实施 ⇒ 前提缺失")
    print("  · 该局限已登记为 L6（已知并接受的残余）")
    print("  ⇒ **S2 判定为「不适用」**")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  S2 判定为『不适用』的证据链完整（未修改任何文件）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
