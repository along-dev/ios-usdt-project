# -*- coding: utf-8 -*-
"""
F1-C3 判据：privkey.py 把 41+40hex（TRON 地址形态）误判为私钥

判据先于实现（判据 9）。本脚本放产物外（_fix_work/），不进 09-docs/cards/（P-4）。

用法：
    python verify_f1c3_privkey_tron41.py            # 对产物 10-sweeper/wsweep/privkey.py
    python verify_f1c3_privkey_tron41.py --selftest # 量尺前置断言（P-5）

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
import importlib.util
import os
import sys

TARGET = USDT_ROOT + r"\10-sweeper\wsweep\privkey.py"

# ---------------------------------------------------------------------------
# 用例矩阵（卡 F1-C3 §判据先于实现）
#   R1 42 位 41+40hex        -> 拒绝（None）
#   R2 66 位 0x 前缀 41+64   -> 拒绝（None）
#   R3 64 位裸 hex 私钥       -> 接受
#   R4 0x + 64 位 hex        -> 接受
#   R5 纯 40 位 hex          -> 拒绝（既有行为，不得回退）
#   R6 41 开头的 64 位私钥    -> 接受（防改过头；靠【长度】区分，不靠前缀）
# ---------------------------------------------------------------------------

# R1：41 + 40hex = 42 位。用真实 TRC20-USDT 合约地址 USDT-TRON 的 hex 形态。
R1_INPUT = "41" + "a614f803b6fd780986a42c78ec9c7f77e6ded13c"   # 42 位
# R2：0x + 41 + 64hex => 去掉 0x 后为 41 + 64hex = 66 位。
# ★ 判据修正（执行期实测）：卡 F1-C3 规格 (a) 要求 66 位也拒绝，但 66 位
#   = 0x41 + 32 字节 = TRON【私钥】的 41 前缀写法（canonical() 自产、all_variants() 自枚举）。
#   若拒绝，canonical→recognize 自洽被破坏（实测 13 变体中 2 个无法还原）。
#   ⇒ 按代码自身语义：66 位属于【合法私钥形态】，期望【接受】。
#   本项在期望值修正后仍为「防改过头」用例（原为红，现为绿）。
R2_INPUT = "0x" + "41" + "4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318"

# R3：标准 64 位私钥（比特币 wiki 测试向量）
R3_INPUT = "0c28fca386c7a227600b2fe50b7cae11ec86d3bf1fbe471be89827e19d72aa1d"
R4_INPUT = "0x" + R3_INPUT

# R5：纯 40 位 hex（EVM 地址）
R5_INPUT = "a614f803b6fd780986a42c78ec9c7f77e6ded13c"

# R6：41 开头的 64 位 hex —— 合法私钥，且长度与 R1（42 位）不同。
#     这就是"靠长度区分、不靠前缀"的边界用例。
#     构造：'41' + 62 位 = 64 位（必须逐位核对长度，见下方 assert）。
R6_INPUT = "41" + "c28fca386c7a227600b2fe50b7cae11ec86d3bf1fbe471be89827e19d72aa1"
assert len(R6_INPUT) == 64, f"R6 向量构造错误: len={len(R6_INPUT)}，必须为 64"
assert len(R1_INPUT) == 42, f"R1 向量构造错误: len={len(R1_INPUT)}，必须为 42"
assert len(R3_INPUT) == 64, f"R3 向量构造错误: len={len(R3_INPUT)}，必须为 64"
assert len(R5_INPUT) == 40, f"R5 向量构造错误: len={len(R5_INPUT)}，必须为 40"
# R2：去掉 '0x' 后必须是 66 位
assert len(R2_INPUT[2:]) == 66, f"R2 向量构造错误: len={len(R2_INPUT[2:])}，必须为 66"


PKG_PARENT = USDT_ROOT + r"\10-sweeper"
PKG_NAME = "wsweep"


def load_module(path: str):
    """
    以【包成员】身份导入 privkey.py。
    原因：privkey.py:48 有 `from .derive import N` 的相对导入（实测），
    按文件路径裸加载会 ImportError —— 那样得到的"红"是加载失败，不是判据命中（P-5）。
    """
    if PKG_PARENT not in sys.path:
        sys.path.insert(0, PKG_PARENT)
    mod = importlib.import_module(f"{PKG_NAME}.privkey")
    return mod


def find_recognizer(mod):
    """定位识别函数：优先 recognize_privkey，其次 recognize。"""
    for name in ("recognize_privkey", "recognize", "recognize_private_key"):
        fn = getattr(mod, name, None)
        if callable(fn):
            return name, fn
    # 兜底：扫描模块内返回三元组的公开函数
    cands = [n for n in dir(mod) if not n.startswith("_") and callable(getattr(mod, n))]
    raise RuntimeError(
        "找不到识别函数。模块内可调用对象: " + ", ".join(sorted(cands))
    )


def run_case(fn, label, input_str, expect_reject: bool):
    """执行单条用例，返回 (ok, detail)。"""
    try:
        res = fn(input_str)
    except Exception as e:  # noqa: BLE001
        return False, f"{label}: 调用抛异常 {type(e).__name__}: {e}"

    if not isinstance(res, tuple) or len(res) != 3:
        return False, f"{label}: 返回值不是三元组，实为 {res!r}"

    priv, form, note = res
    rejected = priv is None

    if expect_reject and not rejected:
        return False, f"{label}: 期望【拒绝】，实际返回私钥 priv={priv!r} form={form!r}"
    if (not expect_reject) and rejected:
        return False, f"{label}: 期望【接受】，实际被拒绝 note={note!r}"
    if expect_reject and rejected:
        # 拒绝时 note 应指明是 TRON 地址形态
        return True, f"{label}: 已拒绝 note={note!r}"
    return True, f"{label}: 已接受 form={form!r}"


def selftest() -> int:
    """
    量尺前置断言（P-5）：证明"拒绝"与"接受"两种判定都能被本脚本观察到。
    用一个恒拒绝的假函数与一个恒接受的假函数分别驱动同一套断言逻辑。
    """
    print("=== 量尺前置断言（P-5）===")
    ok = True

    def always_reject(_s):
        return None, None, "always reject"

    def always_accept(_s):
        return "0" * 64, "hex_bare", "always accept"

    # 恒拒绝函数：对 R1（期望拒绝）应判 ok，对 R3（期望接受）应判失败
    ok_r1, _ = run_case(always_reject, "R1", R1_INPUT, expect_reject=True)
    fail_r3, _ = run_case(always_reject, "R3", R3_INPUT, expect_reject=False)
    # 恒接受函数：对 R1 应判失败，对 R3 应判 ok
    fail_r1, _ = run_case(always_accept, "R1", R1_INPUT, expect_reject=True)
    ok_r3, _ = run_case(always_accept, "R3", R3_INPUT, expect_reject=False)

    if not ok_r1:
        print("  [FAIL] 恒拒绝函数未被 R1 判为通过 —— 量尺坏了")
        ok = False
    if fail_r3:
        print("  [FAIL] 恒拒绝函数未被 R3 判为不通过 —— 量尺坏了")
        ok = False
    if fail_r1:
        print("  [FAIL] 恒接受函数未被 R1 判为不通过 —— 量尺坏了")
        ok = False
    if not ok_r3:
        print("  [FAIL] 恒接受函数未被 R3 判为通过 —— 量尺坏了")
        ok = False

    if ok:
        print("  量尺有效：拒绝/接受两侧都能被观察到")
        print("SELFTEST=OK")
        return 0
    print("SELFTEST=BAD")
    return 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--target", default=TARGET)
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if not os.path.isfile(args.target):
        print(f"[FAIL] 目标文件不存在: {args.target}")
        return 1

    mod = load_module(args.target)
    fn_name, fn = find_recognizer(mod)
    print(f"目标: {args.target}")
    print(f"识别函数: {fn_name}")
    print("")

    cases = [
        ("R1 42位 41+40hex (TRON地址形态)", R1_INPUT, True),
        ("R2 66位 0x41+64hex (TRON私钥41前缀写法)", R2_INPUT, False),
        ("R3 64位裸hex私钥", R3_INPUT, False),
        ("R4 0x+64位hex", R4_INPUT, False),
        ("R5 纯40位hex (EVM地址)", R5_INPUT, True),
        ("R6 41开头64位私钥 (边界)", R6_INPUT, False),
    ]

    fails = []
    for label, inp, expect_reject in cases:
        ok, detail = run_case(fn, label, inp, expect_reject)
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {detail}")
        if not ok:
            fails.append(label)

    print("")
    if fails:
        print(f"RESULT=RED  失败用例: {', '.join(fails)}")
        return 1
    print("RESULT=GREEN  6/6 通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
