# -*- coding: utf-8 -*-
"""
X3 判据：PYTHONIOENCODING 前置写入规则（把 P-10 机械化）。

★ 方案 :262 定档 R1。

★ 现状（调度实测）：
   verify_*.py 共 52 个；已设编码 5 个；未设编码 47 个。
   ★ 其中【真正有崩溃风险】的 34 个（未设编码 + 含非 GBK 字符 ⇒/→/✓ 等）。

★ 本卡目标：把「靠调用方记得设环境变量」变成「脚本自带」。

用法：
    python verify_x3_encoding.py              # 全量
    python verify_x3_encoding.py --selftest   # 量尺前置断言（P-5）

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
import glob
import hashlib
import io
import os
import re
import subprocess
import sys

IOS = IOS_ROOT
D = os.path.join(IOS, "_integration", "_fix_work")
HEADER = os.path.join(D, "_py_header.txt")
RULES = USDT_ROOT + r"\09-docs\reports\开发规则与调度说明.md"
MANIFEST = USDT_ROOT + r"\_manifest.sha256"

# 非 GBK 可编码字符（会触发生 P-10 的 UnicodeEncodeError）
CHECK_CHARS = "\u2713\u2717\u2192\u21d2\u2022\u25cf\u25b6\u2716\u26a0"

# ★ 阈值：未设编码的脚本数
THRESHOLD = 5

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
    return io.open(p, encoding="utf-8", errors="replace").read()


def scan():
    """
    返回 (has_enc, no_enc, risky)。

    ★★ 修正（2026-09-30，执行者指出 + 调度确认）：
      初版口径 `("PYTHONIOENCODING" in s) or ("reconfigure" in s)` **有漏洞**：
      某些脚本**只在 docstring 里写了运行说明** `$env:PYTHONIOENCODING='utf-8'`，
      **没有任何真编码代码**，却被误判为"已设"而**幂等跳过** ——
      清空环境变量后**仍然照崩（EXIT=1）**。
      ⇒ 正确口径：**必须存在【真正的代码】**，而非仅仅字符串提及。
    """
    files = sorted(glob.glob(os.path.join(D, "verify_*.py")))
    has_enc, no_enc, risky = [], [], []
    # ★ 真编码代码的正则（容忍 `os.` / `_os.` 两种别名）
    REAL_ENC = re.compile(
        r"(?:"
        r"(?:_?os)\.environ\.setdefault\s*\(\s*[\"']PYTHONIOENCODING[\"']"
        r"|(?:_?sys)\.(?:stdout|stderr)\.reconfigure\s*\("
        r")"
    )
    for p in files:
        try:
            s = read(p)
        except Exception:
            continue
        base = os.path.basename(p)
        if REAL_ENC.search(s):
            has_enc.append(base)
            continue
        no_enc.append(base)
        hits = [c for c in CHECK_CHARS if c in s]
        if hits:
            risky.append((base, "".join(hits)))
    return has_enc, no_enc, risky


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    if os.path.isdir(D):
        n = len(glob.glob(os.path.join(D, "verify_*.py")))
        print(f"  {os.path.relpath(D, IOS)} 存在，含 {n} 个 verify_*.py")
        if n == 0:
            print("  [FAIL] 0 个脚本 ⇒ 量尺可能坏了")
            ok = False
    else:
        print(f"  [FAIL] 目录缺失: {D}")
        ok = False
    print(f"  _py_header.txt: {'存在' if os.path.isfile(HEADER) else '不存在（待建）'}")
    print(f"  规则手册: {'存在' if os.path.isfile(RULES) else '[FAIL] 缺失'}")
    if not os.path.isfile(RULES):
        ok = False
    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== X3 判据：PYTHONIOENCODING 前置写入 ===")
    print("")

    has_enc, no_enc, risky = scan()
    total = len(has_enc) + len(no_enc)
    print(f"  脚本总数 {total}；已设编码 {len(has_enc)}；未设编码 {len(no_enc)}；"
          f"★ 有崩溃风险 {len(risky)}")
    print("")

    # ---- N1: 未设编码数 <= 阈值 ----
    rec(f"N1 未设编码脚本数 <= {THRESHOLD}", len(no_enc) <= THRESHOLD,
        f"实际 {len(no_enc)}" + (f"（仍超阈值）" if len(no_enc) > THRESHOLD else ""))
    if no_enc and len(no_enc) <= 15:
        print(f"    未设编码: {no_enc}")
    elif no_enc:
        print(f"    未设编码（前 10）: {no_enc[:10]} …")

    # ---- N1b: 有崩溃风险数 == 0 ----
    rec("N1b ★ 有崩溃风险的脚本数 == 0", len(risky) == 0,
        f"实际 {len(risky)}" + (f"：{[r[0] for r in risky[:5]]}" if risky else " ✓"))

    # ---- N2: 头部模板 ----
    print("")
    if os.path.isfile(HEADER):
        hs = read(HEADER)
        has_rc = "reconfigure" in hs
        has_env = "PYTHONIOENCODING" in hs
        rec("N2 _py_header.txt 存在且含 reconfigure + PYTHONIOENCODING",
            has_rc and has_env,
            f"reconfigure={has_rc} env={has_env}（{os.path.getsize(HEADER)} B）")
    else:
        rec("N2 _py_header.txt 存在", False, "★ 不存在")

    # ---- N3: 真跑验证（不设 PYTHONIOENCODING） ----
    print("")
    print("N3 ★ 真跑验证（★ 清空 PYTHONIOENCODING 后跑，证明脚本自带编码）:")
    # 选 3 个改造后的脚本做抽样（优先选有崩溃风险的）
    samples = [r[0] for r in risky[:0]] or []
    # 优先用"已设编码"的脚本做正样本
    samples = has_enc[:3] if has_enc else []
    if not samples:
        print("  [SKIP] 无已改造脚本可抽样 —— SKIP 不等于 PASS（P-13）")
    else:
        env = dict(os.environ)
        env.pop("PYTHONIOENCODING", None)          # ★ 关键：清掉，模拟"调用方忘了设"
        for name in samples:
            p = os.path.join(D, name)
            try:
                r = subprocess.run([sys.executable, p, "--selftest"],
                                   env=env, capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", timeout=180)
                ok = r.returncode in (0, 2)         # 2 = selftest 失败也算"没崩"
                rec(f"N3 {name} 在不设 PYTHONIOENCODING 下不崩", ok,
                    f"EXIT={r.returncode}")
                if not ok:
                    print(f"      stderr: {(r.stderr or '')[-200:]}")
            except subprocess.TimeoutExpired:
                rec(f"N3 {name}", False, "★ 超时")
            except Exception as e:
                rec(f"N3 {name}", False, f"★ {e}")

    # ---- N4: 规则手册已补说明 ----
    print("")
    if os.path.isfile(RULES):
        rs = read(RULES)
        # 找 P-10 之后是否提到 X3 / reconfigure
        m = re.search(r"P-10.*?(?=\n\| \*\*P-1[12]|\n###)", rs, re.S)
        seg = m.group(0) if m else ""
        has_x3 = ("X3" in seg) or ("reconfigure" in seg)
        rec("N4 规则手册的 P-10 已补『X3 落实』说明", has_x3,
            "已补 ✓" if has_x3 else "★ 未补")

    # ---- N5: 未改产物代码 ----
    print("")
    print("N5 ★ 未改任何产物代码（01–06 目录）:")
    print("    （抽查关键文件的 sha256 与既往基线一致）")
    checks = [
        (USDT_ROOT + r"\02-backend-node\src_restored\plugins\api\routes\landing.js",
         "3208c207bf423c8d99577c0508e9b6cc809f471dcd590ee0e96b87906e7de632"),
        (USDT_ROOT + r"\05-ios\coruna\implant_ops.js",
         "43fb7b6f940c62237d0db869eec647704d155cfed69ea6e4b5da4786c555c286"),
    ]
    for p, want in checks:
        if os.path.isfile(p):
            cur = sha256(p)
            rec(f"N5 {os.path.basename(p)} 未改", cur == want, f"{cur[:16]}…")

    # ---- N6: 守护 ----
    print("")
    if os.path.isfile(MANIFEST):
        rec("N6 _manifest.sha256 未改", sha256(MANIFEST) == MANIFEST_SHA,
            f"{sha256(MANIFEST)[:16]}…")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  判据脚本自带 UTF-8 输出，不再依赖调用方设置")
    return 0


if __name__ == "__main__":
    sys.exit(main())
