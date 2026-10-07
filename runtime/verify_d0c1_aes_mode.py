# -*- coding: utf-8 -*-
"""
D0-C1 判据：bdecrypt.py 的 AES 模式选择必须按 mode 字符串，且与 bstage*.py 一致。

★★ 缺陷（已由调度实跑确证，2026-09-29）：
   bdecrypt.py 从字节码还原出 mode = "AES/CTR/NoPadding"（:22-23、:42-43 已解出），
   但 :44-50 的分支【只看 len(parts)，不看 parts[1]】：
       if len(parts) == 3:      cipher = AES.new(KEY, AES.MODE_CBC, iv)   ← 一律 CBC
   ⇒ 真实需要 CTR，代码却用 CBC ⇒ 解出乱码（且【不报错】，静默出错）。

   ★ 对照证据：同目录 bstage.py:13-14 / bstage2.py:12 / bstage3.py:12
     三个脚本【全部】用 MODE_CTR + Counter.new(128, initial_value=iv)。
     ⇒ 同一套数据，唯独 bdecrypt.py 用 CBC。

用法：
    python verify_d0c1_aes_mode.py              # 全量
    python verify_d0c1_aes_mode.py --selftest   # 量尺前置断言（P-5）

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
import os
import re
import sys

ROOT = USDT_ROOT + r"\06-android\tools"
BDECRYPT = os.path.join(ROOT, "bdecrypt.py")
BSTAGES = [os.path.join(ROOT, "bstage.py"),
           os.path.join(ROOT, "bstage2.py"),
           os.path.join(ROOT, "bstage3.py")]

_results = []


def rec(name, ok, detail):
    _results.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def read(p):
    return open(p, encoding="utf-8", errors="replace").read()


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    for p in [BDECRYPT] + BSTAGES:
        if os.path.isfile(p):
            print(f"  存在: {os.path.basename(p)} ({os.path.getsize(p)} B)")
        else:
            print(f"  [FAIL] 缺失: {p}")
            ok = False

    # 量尺有效性：正则必须能在合成样本上区分 CBC / CTR
    cbc = "cipher = AES.new(KEY, AES.MODE_CBC, iv)"
    ctr = "pt = AES.new(KEY, AES.MODE_CTR, counter=ctr).decrypt(ct)"
    if re.search(r"MODE_CBC", cbc) and re.search(r"MODE_CTR", ctr):
        print("  模式有效：可区分 MODE_CBC 与 MODE_CTR")
    else:
        print("  [FAIL] 模式失效")
        ok = False

    # ★ 关键：必须确认 bdecrypt.py 当前【确实】含 MODE_CBC（否则本判据的前提不成立）
    src = read(BDECRYPT)
    if "MODE_CBC" in src:
        print("  当前 bdecrypt.py 含 MODE_CBC（判据前提成立）")
    else:
        print("  当前 bdecrypt.py 不含 MODE_CBC（可能已修，或文件被换）")

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== D0-C1 bdecrypt.py AES 模式选择判据 ===")
    print("")

    src = read(BDECRYPT)

    # ---- B1: 必须按 parts[1] 选算法（而非只看 len）----
    #
    # ★★ 弱断言修正（自查，2026-09-29）：
    #   初版只判 `parts[1]` 是否【出现过】⇒ 匹配到 :47 的 `parts[1] == "ECB"`（假绿）。
    #   但 :47 只在 `len(parts)==2` 时才看它；真实的 `AES/CTR/...`（len==3）
    #   【根本不到 parts[1]】⇒ 这才是缺陷本体。
    #   ⇒ 正确判据：必须存在【以 parts[1] 为分派依据】的结构，且 CTR 分支可达。
    print("B1 必须按 mode 字符串的算法段选择（★ 防弱断言）:")
    # 提取包含 parts[1] 的判断行
    alg_lines = [m for m in re.findall(r"^[^\n]*parts\s*\[\s*1\s*\][^\n]*$", src, re.M)]
    print("    含 parts[1] 的判断行:")
    for l in alg_lines:
        print(f"      {l.strip()}")
    # 真正的分派：parts[1] 与某种算法名比较，且该分支能走到 CTR
    dispatch_ctr = re.search(r"parts\s*\[\s*1\s*\]\s*==\s*['\"]CTR['\"]", src) is not None
    dispatch_generic = re.search(
        r"parts\s*\[\s*1\s*\]\s*\.\s*upper\s*\(\s*\)", src) is not None or \
        re.search(r"alg\s*=\s*parts\s*\[\s*1\s*\]", src) is not None
    ok1 = dispatch_ctr or dispatch_generic
    rec("B1 存在按 parts[1] 的算法分派（能选中 CTR）", ok1,
        f"dispatch_ctr={dispatch_ctr} dispatch_generic={dispatch_generic}"
        + ("" if ok1 else "  ★ 仍只看段数 ⇒ 缺陷"))
    if alg_lines and not ok1:
        print("      ★ 注意：文件里虽出现 parts[1]，但仅用于 ECB 特判，非通用分派")

    # ---- B2: 必须存在 CTR 分支 ----
    print("")
    print("B2 必须存在 CTR 分支:")
    has_ctr = "MODE_CTR" in src
    rec("B2 含 AES.MODE_CTR", has_ctr, "已含 CTR" if has_ctr else "★ 无 CTR ⇒ 必错")

    # ---- B3: CTR 必须用正确的 counter（与 bstage 一致）----
    print("")
    print("B3 CTR 必须使用 Counter（initial_value=iv）:")
    has_counter = re.search(r"Counter\.new\s*\(\s*128", src) is not None
    rec("B3 含 Counter.new(128, initial_value=iv)", has_counter,
        "已用 Counter" if has_counter else "★ CTR 未用 Counter 会解错")

    # ---- B4: ★ 与 bstage*.py 的一致性（对照）----
    print("")
    print("B4 与 bstage*.py 的算法一致性（对照）:")
    stage_modes = {}
    for p in BSTAGES:
        if os.path.isfile(p):
            s = read(p)
            stage_modes[os.path.basename(p)] = (
                "CTR" if "MODE_CTR" in s else ("CBC" if "MODE_CBC" in s else "?"))
    for k, v in stage_modes.items():
        print(f"    {k}: {v}")
    all_ctr = all(v == "CTR" for v in stage_modes.values())
    rec("B4 三个 bstage 全部为 CTR", all_ctr, f"{stage_modes}")

    # ---- B5: 防改过头 —— 不得删除 bstage*.py 的功能 ----
    print("")
    print("B5 防改过头（bstage*.py 不得被本卡改动）:")
    for p in BSTAGES:
        if os.path.isfile(p):
            s = read(p)
            rec(f"B5 {os.path.basename(p)} 仍为 CTR 且含 Counter",
                ("MODE_CTR" in s) and ("Counter.new" in s),
                "OK" if ("MODE_CTR" in s and "Counter.new" in s) else "★ 被改坏")

    # ---- B6: 不得残留「兜底一律 CBC」----
    print("")
    print("B6 不得残留无条件 CBC 兜底:")
    # 找形如  else:  ... MODE_CBC  且无算法判断 的兜底
    fallback = re.findall(r"else\s*:\s*\n\s*cipher\s*=\s*AES\.new\([^)]*MODE_CBC", src)
    rec("B6 无「else 一律 CBC」兜底", len(fallback) == 0,
        f"命中 {len(fallback)} 处" + ("（★ 仍在）" if fallback else ""))

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  bdecrypt.py 已按 mode 选算法，且与 bstage*.py 一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
