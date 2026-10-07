# -*- coding: utf-8 -*-
"""
F1-C2 交叉验证：两处口径（Sk() 与 CollectResult）必须等价。
方法：从两个源文件里【独立抽取】私域分支的关键口径要素，逐项比对。
这是"复制口径"是否抄准的直接证据。
"""
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
import os
import re
import sys

ROOT = USDT_ROOT
SCAN = os.path.join(ROOT, "01-backend-go", "blockchain", "scan.go")
CR = os.path.join(ROOT, "01-backend-go", "service", "app", "collect_result.go")


def strip_comments(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return "\n".join(ln.split("//")[0] for ln in src.splitlines())


def extract_private_block(src, which):
    """
    抽出私域块 —— ★ 必须按【块边界】截取，不能用固定行数窗口。
    首版用 +40 行固定窗口，越界进了公域三笔，导致
    「私域块内无 role 1/2/3」误报 False（P-5 第 10 例）。
    """
    s = strip_comments(src)
    lines = s.splitlines()

    def find_block_end(start_line_idx):
        """
        从 start 行起，按【大括号配对】找到块结束行索引。
        ★ 不用"遇到 return 就停"的启发式 —— F1-C9 在私域块内新增了一个
          【更内层的 return e】（校验失败分支），启发式会把它误判为块尾，
          导致抽取段过早截断 ⇒ role=4 / totalAmount 都不在段内 ⇒ 假红。
          （P-5 第 12 例；与 F1-C6 的 `[^}]*` 提前终止同族：
           块边界必须靠配对，不能靠启发式。）
        """
        depth = 0
        started = False
        for j in range(start_line_idx, len(lines)):
            for ch in lines[j]:
                if ch == "{":
                    depth += 1
                    started = True
                elif ch == "}":
                    depth -= 1
                    if started and depth == 0:
                        return j
        return len(lines) - 1

    if which == "scan":
        idx = next((i for i, l in enumerate(lines)
                    if re.search(r"Role\s*=\s*4\b", l)), None)
        if idx is None:
            return None
        # 回溯找 `} else {`
        start = idx
        for j in range(idx, max(0, idx - 25), -1):
            if re.search(r"\}\s*else\s*\{", lines[j]):
                start = j
                break
        end = find_block_end(start)
        return "\n".join(lines[start:end + 1])
    else:
        idx = next((i for i, l in enumerate(lines) if re.search(r"Region\s*==\s*2", l)), None)
        if idx is None:
            return None
        end = find_block_end(idx)
        return "\n".join(lines[idx:end + 1])


print("=== F1-C2 口径等价性交叉验证 ===")
print("")

# ★ 量尺自检：块边界提取必须【止于块尾】，不得越界进公域，
#   且【内层 return 不得导致截断】（F1-C9 新增校验分支后暴露的缺陷）。
_fake = """if wallet.Region == 2 {
    if chk(x) != nil {
        return e
    }
    mkBill(4, id, totalAmount)
    return nil
}
mkBill(1, sys, systemAmount)
mkBill(2, cus, customAmount)
"""
_l = strip_comments(_fake).splitlines()


def _fake_find_block_end(start_idx):
    depth = 0
    started = False
    for j in range(start_idx, len(_l)):
        for ch in _l[j]:
            if ch == "{":
                depth += 1
                started = True
            elif ch == "}":
                depth -= 1
                if started and depth == 0:
                    return j
    return len(_l) - 1


_end = _fake_find_block_end(0)
_seg = "\n".join(_l[0:_end + 1])
_ok_boundary = (
    ("mkBill(1" not in _seg)        # 未越界进公域
    and ("mkBill(4" in _seg)        # 含私域主体
    and ("return e" in _seg)        # ★ 内层 return 未导致截断
)
if _ok_boundary:
    print("  量尺：块边界提取有效（止于配对块尾；内层 return 不截断；不越界进公域）")
else:
    print(f"  [FAIL] 量尺：块边界提取异常 -> seg={_seg!r}")
    sys.exit(2)

scan_priv = extract_private_block(open(SCAN, encoding="utf-8").read(), "scan")
cr_priv = extract_private_block(open(CR, encoding="utf-8").read(), "cr")

# ★ UsdtNum 的折算在 mkBill 闭包内统一完成（对 role 1/2/3/4 一致），
#   故断言方式为「私域调用了 mkBill」+「mkBill 内有 radio 折算」，而非私域块字面含 radio。
CR_FULL = strip_comments(open(CR, encoding="utf-8").read())
mkbill_has_radio = bool(re.search(r"UsdtNum:\s*num\.Mul\(radio\)", CR_FULL))

if scan_priv is None:
    print("[FAIL] scan.go 无 Region==2 分支（口径基准缺失）")
    sys.exit(1)
if cr_priv is None:
    print("[FAIL] collect_result.go 无 Region==2 分支（本卡未实现）")
    sys.exit(1)

# 口径要素：(名称, 正则, 期望)
CHECKS = [
    ("settlement 定位 user_id = -1", r"user_id\s*=\s*-1"),
    ("bill 角色 role = 4", r"mkBill\(\s*4\s*,|Role:\s*4\b|Role\s*=\s*4\b"),
    ("金额 = totalAmount 全额", r"totalAmount"),
    # ★ UsdtNum 由 mkBill 闭包统一折算（对 4 种 role 一致）⇒ 断言"私域经 mkBill 落账"即可，
    #   另单独断言 mkBill 内确有 radio 折算（见下方）。
    ("私域经 mkBill 落账", r"mkBill\(\s*4\s*,"),
]

fails = []
print(f"{'口径要素':<32} {'scan.go(Sk)':<14} {'collect_result.go':<18} 结论")
print("-" * 80)
for label, pat in CHECKS:
    a = bool(re.search(pat, scan_priv))
    b = bool(re.search(pat, cr_priv))
    # scan.go 的私域不经 mkBill（它是内联构造），故"私域经 mkBill"只对 CR 断言
    if label == "私域经 mkBill 落账":
        ok = b
        verdict = "CR 已委托" if b else "CR 未委托"
    else:
        ok = a and b
        verdict = "一致" if ok else ("缺失(CR)" if a and not b else ("仅CR" if b and not a else "两者皆缺"))
    if not ok:
        fails.append(label)
    print(f"{label:<32} {str(a):<14} {str(b):<18} {verdict}")

# ★ mkBill 内必须有 radio 折算（保证 role=4 的 UsdtNum 与公域同法）
print("")
print(f"{'mkBill 内 UsdtNum 按 radio 折算':<32} {'—':<14} {str(mkbill_has_radio):<18} "
      f"{'已折算是' if mkbill_has_radio else '缺失'}")
if not mkbill_has_radio:
    fails.append("mkBill 无 radio 折算")

print("")
# 反向：私域块内不得出现公域三笔的扣减
cr_no_deduct = not re.search(r"Sub\(\s*systemAmount\s*\)", cr_priv)
scan_no_deduct = not re.search(r"Sub\(\s*decSystem\s*\)", scan_priv)
print(f"私域块内无「扣平台费」: Sk={scan_no_deduct} CR={cr_no_deduct}")
if not (cr_no_deduct and scan_no_deduct):
    fails.append("私域块含公域扣减")

# 反向：私域块内不得 mkBill(1/2/3)
cr_no_public = not re.search(r"mkBill\(\s*[123]\s*,", cr_priv)
print(f"私域块内无 role 1/2/3: CR={cr_no_public}")
if not cr_no_public:
    fails.append("私域块含公域三笔")

print("")
if fails:
    print(f"RESULT=RED  不等价要素: {fails}")
    sys.exit(1)
print("RESULT=GREEN  两处私域口径要素逐项等价")
sys.exit(0)
