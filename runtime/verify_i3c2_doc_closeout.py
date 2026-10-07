# -*- coding: utf-8 -*-
"""
I3-C2 判据：收口原审核报告与需求文档的遗留矛盾。

判据先于实现（判据 9）。本脚本放产物外（_fix_work/），不进 09-docs/cards/（P-4）。

★ 与卡内 verify 的差异（执行期裁决，理由见台账 L002）：
   卡 I3-C2 的 verify 写 `grep -c '由二期升入' 需求文档.md  # 须 0`。
   但实测该串出现在 §3.3【裁决留痕表】的「原状态」列 —— 属**历史记录**。
   V0《裁决引用纪律》第 3 条明令「**不得就地改写历史条目**」。
   ⇒ 判据改为【语义断言】：该串**可以**存在，但**不得出现在当前状态描述中**
     （即必须位于 §3.3 裁决留痕区块内）。

用法：
    python verify_i3c2_doc_closeout.py              # 对产物
    python verify_i3c2_doc_closeout.py --selftest   # 量尺前置断言（P-5）

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
REQ = os.path.join(ROOT, "09-docs", "analysis", "需求文档.md")
OPT = os.path.join(ROOT, "09-docs", "reports", "全量审核结论与优化方案.md")
INDEX_MD = os.path.join(ROOT, "09-docs", "INDEX.md")


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def find_heading_span(text, heading_pattern):
    """
    找到标题所在的小节范围 [start, end)。
    返回 (start_idx, end_idx) 或 None。

    ★ 边界规则：切到【下一个 level <= 本标题 level】的标题行之前。
      首版用 `^#{1,%d} ` 拼正则，在伪造样本上算错级别导致整段切到文末
      —— 属量尺缺陷（自检已抓到，见 --selftest）。
    """
    m = re.search(heading_pattern, text, re.M)
    if not m:
        return None
    start = m.start()
    level = len(re.match(r"#+", m.group(0)).group(0))
    # 逐行扫描找下一个同级或更高级标题
    pos = m.end()
    for line_m in re.finditer(r"^(#{1,6}) ", text[pos:], re.M):
        nxt_level = len(line_m.group(1))
        if nxt_level <= level:
            return (start, pos + line_m.start())
    return (start, len(text))


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True

    # 小节范围定位器必须有效
    fake = """# 文档
## 1 甲
甲内容
### 1.1 子节
子内容（应属甲）
## 2 乙
乙内容（不属甲）
"""
    span = find_heading_span(fake, r"^## 1 甲")
    if not span:
        print("  [FAIL] 小节定位失败")
        ok = False
    else:
        seg = fake[span[0]:span[1]]
        if "甲内容" not in seg:
            print(f"  [FAIL] 未包含本小节内容: {seg!r}")
            ok = False
        elif "乙内容" in seg:
            print(f"  [FAIL] 越界到下一同级小节: {seg!r}")
            ok = False
        elif "子内容" not in seg:
            print(f"  [FAIL] 未包含子节内容（子节应属本小节）: {seg!r}")
            ok = False
        else:
            print("  小节范围定位有效（含子节、止于下一个同级标题）")

    # 反向：不存在的标题必须返回 None（否则会误判"在留痕内"）
    if find_heading_span(fake, r"^## 不存在的标题"):
        print("  [FAIL] 不存在的标题未返回 None")
        ok = False
    else:
        print("  不存在的标题正确返回 None")

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    fails = []

    # --- 断言 1（语义版）：'由二期升入' 只允许出现在 §3.3 裁决留痕内 ---
    print("断言 1（语义版）：'由二期升入' 必须仅出现在 §3.3 裁决留痕区块内")
    req = read(REQ)
    span = find_heading_span(req, r"^#{2,3} .*3\.3.*一期范围裁决")
    if not span:
        print("  [FAIL] 找不到 §3.3 裁决留痕小节")
        fails.append("no-3.3-section")
    else:
        seg = req[span[0]:span[1]]
        total = req.count("由二期升入")
        inside = seg.count("由二期升入")
        print(f"  全文出现 {total} 次；其中 §3.3 区块内 {inside} 次")
        if total != inside:
            print(f"  [FAIL] 有 {total - inside} 次出现在 §3.3 之外（属当前状态描述，不允许）")
            fails.append("outside-3.3")
        else:
            print("  [PASS] 全部位于裁决留痕区块内（符合 V0 引用纪律：不改写历史）")

    # --- 断言 2：'iOS 链不可用' 须 >=1（当前状态已显式登记） ---
    print("")
    print("断言 2：'iOS 链不可用' 须 >=1")
    n2 = req.count("iOS 链不可用")
    if n2 >= 1:
        print(f"  [PASS] 命中 {n2} 次")
    else:
        print("  [FAIL] 未登记 iOS 链一期不可用")
        fails.append("no-ios-unavailable")

    # --- 断言 3：'已修复' 须 >=4 ---
    print("")
    print("断言 3：'已修复' 须 >=4（全量审核结论与优化方案.md）")
    opt = read(OPT)
    n3 = opt.count("已修复")
    if n3 >= 4:
        print(f"  [PASS] 命中 {n3} 次")
    else:
        print(f"  [FAIL] 仅 {n3} 次，不足以标注 4 条 P0 已修")
        fails.append("insufficient-fixed-marks")

    # --- 断言 4：INDEX.md 须含"按模块的当前状态总表" ---
    print("")
    print("断言 4：INDEX.md 须含按模块的当前状态总表")
    idx = read(INDEX_MD)
    if "按模块的当前状态总表" in idx:
        print("  [PASS] 已建总表")
    else:
        print("  [FAIL] 未建按模块状态总表")
        fails.append("no-module-status-table")

    # --- 断言 5：INDEX.md 须指向时效索引（防下个会话误读） ---
    print("")
    print("断言 5：INDEX.md 须指向 reports/文档时效索引.md")
    if "文档时效索引.md" in idx:
        print("  [PASS] 已指向时效索引")
    else:
        print("  [FAIL] 未指向时效索引")
        fails.append("no-freshness-index-link")

    print("")
    if fails:
        print(f"RESULT=RED  失败项: {fails}")
        return 1
    print("RESULT=GREEN  文档矛盾已收口、状态表已建、时效入口已连")
    return 0


if __name__ == "__main__":
    sys.exit(main())
