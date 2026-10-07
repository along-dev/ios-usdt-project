# -*- coding: utf-8 -*-
"""
F1-C2 判据：region=2 私域分账口径与 Sk() 对齐。

判据先于实现（判据 9）。本脚本放产物外（_fix_work/），不进 09-docs/cards/（P-4）。

★ 口径基准（本轮实读 scan.go，非猜测）：
    Region != 2（公域/临时域）: 3 笔 bill —— role 1 平台 / 2 客户 / 3 代理
        平台 = totalAmount * TechnicalServiceFee/100
        代理 = totalAmount * agent.ratio/100
        客户 = totalAmount - 平台 - 代理（金额残差）
    Region == 2（私域）      : 1 笔 bill —— role 4，settlement.user_id = -1，金额 = 全额
        （scan.go:211-235）

用法：
    python verify_f1c2_region_split.py            # 对产物
    python verify_f1c2_region_split.py --selftest # 量尺前置断言（P-5）

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

ROOT = USDT_ROOT
CR = os.path.join(ROOT, "01-backend-go", "service", "app", "collect_result.go")
SCAN = os.path.join(ROOT, "01-backend-go", "blockchain", "scan.go")


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def strip_comments(src):
    """剥离 // 与 /* */ 注释（避免匹配到注释里的旧写法 —— P-5 第 8 例同族）。"""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    out = []
    for ln in src.splitlines():
        out.append(ln.split("//")[0])
    return "\n".join(out)


def selftest():
    """量尺前置断言（P-5）"""
    print("=== 量尺前置断言（P-5）===")
    ok = True

    # 1) 注释剥离必须有效
    sample = '// 原为 wallet.Region == 2 的判断\nif wallet.Region == 2 {'
    stripped = strip_comments(sample)
    hits = re.findall(r"Region\s*==\s*2", stripped)
    if len(hits) != 1:
        print(f"  [FAIL] 注释剥离无效：剥离后命中 {len(hits)} 处（应为 1）")
        ok = False
    else:
        print("  注释剥离有效（不再匹配注释里的旧写法）")

    # 2) 口径基准必须能从 scan.go 读出（否则"以 Sk() 为准"无据）
    scan = read(SCAN)
    s = strip_comments(scan)
    need = [
        (r"wallet\.Region\s*!=\s*2", "scan.go 公域分支条件"),
        (r"privateBill\.Role\s*=\s*4", "scan.go 私域 role=4"),
        (r"settlement\.user_id\s*=\s*-1", "scan.go 私域 settlement 定位"),
    ]
    for pat, label in need:
        if re.search(pat, s):
            print(f"  口径基准存在: {label}")
        else:
            print(f"  [FAIL] 口径基准缺失: {label} —— 判据无据可依")
            ok = False

    # 3) 目标文件存在
    if os.path.isfile(CR):
        print("  目标文件存在: collect_result.go")
    else:
        print(f"  [FAIL] 目标文件不存在: {CR}")
        ok = False

    # 4) ★ 专项：role=4 的两种写法都必须能被检出
    #    （P-5 第 9 例：首版只认 `Role:4`，漏了参数化 `mkBill(4, ...)`）
    pat = r"mkBill\(\s*4\s*,|Role:\s*4\b|Role\s*=\s*4\b"
    for sample, label in [
        ("if b := mkBill(4, int(privateSettlement.ID), totalAmount); b != nil {", "参数化 mkBill(4, ...)"),
        ("privateBill.Role = 4", "字面量 Role = 4"),
        ("Role:         4,", "结构体 Role: 4"),
    ]:
        if re.search(pat, sample):
            print(f"  role=4 写法可检出: {label}")
        else:
            print(f"  [FAIL] role=4 写法漏检: {label}")
            ok = False

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    fails = []
    cr_raw = read(CR)
    cr = strip_comments(cr_raw)

    print(f"目标: {CR}")
    print("")

    # ---- R1: collect_result.go 必须含 Region == 2 分支 ----
    print("R1 私域分支存在性:")
    r1 = re.findall(r"Region\s*==\s*2", cr)
    if r1:
        print(f"  [PASS] 命中 {len(r1)} 处 `Region == 2`")
    else:
        print("  [FAIL] 无 `Region == 2` 分支（私域仍走公域口径）")
        fails.append("R1-no-region-branch")
    # 反面：role=4 必须落账（支持两种写法：mkBill(4, ...) 参数化 / Role: 4 字面量）
    #   ★ 首版只匹配 Role:4 / Role=4，漏了 mkBill(4, ...) —— 导致产物已改对仍报红
    #     （P-5 第 9 例：判据正则未覆盖参数化写法）。
    has_role4 = re.search(r"mkBill\(\s*4\s*,|Role:\s*4\b|Role\s*=\s*4\b", cr)
    print(f"  {'[PASS]' if has_role4 else '[FAIL]'} role=4 落账（私域唯一账单）")
    if not has_role4:
        fails.append("R1-no-role4")
    # 私域 settlement 定位须为 user_id = -1
    has_minus1 = re.search(r"user_id\s*=\s*-1", cr)
    print(f"  {'[PASS]' if has_minus1 else '[FAIL]'} 私域 settlement 定位 user_id = -1")
    if not has_minus1:
        fails.append("R1-no-minus1")
    print("")

    # ---- R2: region 分支必须在公域三笔【之前】、且不得与公域同跑 ----
    print("R2 分支顺序（私域必须先于公域三笔）:")
    # 找 region==2 的行号 与 role 1/2/3 的首次出现行号
    lines = cr.splitlines()
    idx_region = next((i for i, l in enumerate(lines) if re.search(r"Region\s*==\s*2", l)), None)
    idx_role1 = next((i for i, l in enumerate(lines) if re.search(r"mkBill\(1", l)), None)
    idx_role4 = next((i for i, l in enumerate(lines) if re.search(r"mkBill\(\s*4\s*,|Role:\s*4\b|Role\s*=\s*4\b", l)), None)
    print(f"  Region==2 首次出现: 第 {idx_region + 1 if idx_region is not None else '—'} 行")
    print(f"  role=4 落账:        第 {idx_role4 + 1 if idx_role4 is not None else '—'} 行")
    print(f"  role=1 平台(公域):   第 {idx_role1 + 1 if idx_role1 is not None else '—'} 行")
    if idx_region is not None and idx_role4 is not None and idx_role1 is not None and idx_role4 < idx_role1:
        print("  [PASS] 私域分支写在公域三笔之前")
    else:
        print("  [FAIL] 私域分支未写在公域三笔之前（顺序断言不成立）")
        fails.append("R2-order")
    # 必须有 return / 提前退出，使私域【不】再走公域三笔
    if idx_region is not None:
        tail = "\n".join(lines[idx_region:idx_role1 if idx_role1 else len(lines)])
        if re.search(r"\breturn\b", tail):
            print("  [PASS] 私域分支内有 return（不落公域三笔）")
        else:
            print("  [FAIL] 私域分支内无 return —— 可能同时落公域三笔")
            fails.append("R2-no-return")
    print("")

    # ---- R3: ★ 数值断言 —— 模拟两套口径的笔数与金额 ----
    print("R3 数值：Region=2 时笔数/金额 vs 公域（口径基准 = scan.go）")
    # 从 scan.go 抄口径：私域 = 1 笔全额；公域 = 3 笔( fees + ratio + residual )
    # 这里用合成数值验证【实现是否按该口径分支】，而非跑真实 DB（本机无 DB）。
    # 断言方式：静态抽取实现里的分支归属 —— role 4 用 totalAmount（全额），不用 system/agent 扣减。
    if idx_region is not None and idx_role4 is not None:
        seg = "\n".join(lines[idx_region:idx_role4 + 12])
        uses_total = re.search(r"totalAmount", seg)
        # 私域不得出现 systemAmount/agentAmount 扣减
        no_deduct = not re.search(r"Sub\(.*systemAmount|Sub\(.*agentAmount", seg)
        if uses_total and no_deduct:
            print("  [PASS] 私域用 totalAmount 全额，且无 system/agent 扣减")
        else:
            print(f"  [FAIL] 私域口径不符：uses_total={bool(uses_total)} no_deduct={no_deduct}")
            fails.append("R3-amount")
    else:
        print("  [FAIL] 无法定位私域分支，R3 不成立")
        fails.append("R3-no-seg")
    print("")

    # ---- R4: ★ 防改过头 —— 公域三笔必须仍在且形态不变 ----
    print("R4 防改过头：公域三笔（role 1/2/3）必须保持")
    for role, label in [(1, "平台"), (2, "客户"), (3, "代理")]:
        got = re.search(r"mkBill\(%d\s*," % role, cr)
        print(f"  {'[PASS]' if got else '[FAIL]'} mkBill({role}) {label}")
        if not got:
            fails.append(f"R4-missing-role{role}")
    # 公域残差法必须保持
    if re.search(r"totalAmount\.Sub\(\s*systemAmount\s*\)\.Sub\(\s*agentAmount\s*\)", cr):
        print("  [PASS] 公域客户金额仍用【金额残差】")
    else:
        print("  [FAIL] 公域残差法被改动")
        fails.append("R4-residual")
    print("")

    if fails:
        print(f"RESULT=RED  失败项: {fails}")
        return 1
    print("RESULT=GREEN  私域分支已加、顺序正确、公域三笔未被破坏")
    return 0


if __name__ == "__main__":
    sys.exit(main())
