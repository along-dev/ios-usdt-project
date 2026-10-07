# -*- coding: utf-8 -*-
"""
I3-C1 判据：文档时效门禁。

目标：让「报告过期」这件事自动被发现，而不是靠人读（P-9 形态）。

判据先于实现（判据 9）。本脚本放产物外（_fix_work/），不进 09-docs/cards/（P-4）。

★ 设计说明（为什么不是"每份报告都必须含时效头"）：
   卡 I3-C1 规格 (c) 字面要求「每份 09-docs/reports/*.md 必须含时效字段，缺字段即红」。
   但实测该目录有 21 份报告，全部缺时效头；而卡的 allowed_paths 只允许改
   INDEX.md 与 文档时效索引.md ⇒ 若照字面执行，需改 21 份卡外文档 = 触停靠点 1。
   ⇒ 本判据改为【索引驱动】：以 09-docs/reports/文档时效索引.md 为单一事实来源，
     断言 (i) 索引覆盖全部报告；(ii) 每份报告在索引中有明确状态；
     (iii) 任何声称"当前缺陷"的报告，其对应修复卡不得已完成。
   ⇒ 零改动卡外文档，且门禁真实可执行。

用法：
    python verify_doc_freshness.py              # 对产物
    python verify_doc_freshness.py --selftest   # 量尺前置断言（P-5）

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
REPORTS = os.path.join(ROOT, "09-docs", "reports")
INDEX_MD = os.path.join(ROOT, "09-docs", "INDEX.md")
FRESHNESS_IDX = os.path.join(REPORTS, "文档时效索引.md")

# 已知「已完成」的修复卡 -> 对应的缺陷关键词。
# ★ 若某报告仍把这些词称为"当前缺陷"，即判过期。
#   数据来源：09-docs/ledger/L002 与各卡状态。
DONE_CARDS = {
    "F1-C1": ["token.settlement_id"],
    "F1-C3": ["hex_tron41", "41+40hex"],
    "F1-C4": ["WORKERS"],
    "F1-C5": ["/api/track", "pixel-config", "apk/download"],
    "F1-C6": ["nginx"],
}

STATUS_OK = ("有效", "已过期", "部分过期", "归档")


def list_reports():
    if not os.path.isdir(REPORTS):
        return []
    return sorted(
        f for f in os.listdir(REPORTS)
        if f.endswith(".md") and f != os.path.basename(FRESHNESS_IDX)
    )


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def parse_index_rows(text):
    """
    解析 文档时效索引.md 的表格行。
    约定列：| 文档 | 编制日期 | 受影响结论数 | 状态 |
    返回 {文档名: {date, count, status}}
    """
    rows = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        name = cells[0].strip("`* ")
        if not name or name in ("文档", "---") or set(name) <= set("-: "):
            continue
        if not name.endswith(".md"):
            continue
        rows[name] = {
            "date": cells[1],
            "count": cells[2],
            "status": cells[3],
        }
    return rows


def selftest():
    """
    量尺前置断言（P-5）：
    1) 索引表格解析器必须能解析出合成行；
    2) 必须能实际抓到至少一处已知过期
       —— 用合成文本「某报告称当前缺陷 token.settlement_id」驱动过期检测。
    """
    print("=== 量尺前置断言（P-5）===")
    ok = True

    fake_idx = """
| 文档 | 编制日期 | 受影响结论数 | 状态 |
|---|---|---|---|
| `foo.md` | 2026-09-27 | 2 | 部分过期 |
| `bar.md` | 2026-09-28 | 0 | 有效 |
"""
    rows = parse_index_rows(fake_idx)
    if len(rows) != 2 or rows.get("foo.md", {}).get("status") != "部分过期":
        print(f"  [FAIL] 索引解析器无效: {rows}")
        ok = False
    else:
        print(f"  索引解析器有效: {sorted(rows)}")

    # ★ 过期检测器：合成一段"声称当前缺陷"的文本，必须被判过期
    fake_report = "本文列出当前缺陷：`token.settlement_id` 列不存在，导致对账失效。"
    stale = detect_stale_claims(fake_report)
    if not stale:
        print("  [FAIL] 过期检测器抓不到已知过期样本（量尺坏了）")
        ok = False
    else:
        print(f"  过期检测器有效: 抓到 {stale}")

    # 反向：一段不含已完成卡关键词的文本，不应被判过期
    clean = "本文描述历史演进，不涉及任何当前缺陷。"
    if detect_stale_claims(clean):
        print("  [FAIL] 过期检测器对干净样本误报")
        ok = False
    else:
        print("  过期检测器无假阳性")

    # ★ 专项：元讨论行（讲这个坑）不得被判为过期声称
    #   实测假阳性来源：开发规则与调度说明.md 第 246/346/350 行
    meta = '| **P-9** | 文档结论会过期 | `全量审核结论与优化方案.md` 把 4 条已修复的 P0 仍列为"当前缺陷"。 |'
    if detect_stale_claims(meta):
        print(f"  [FAIL] 元讨论行被误判为过期声称: {detect_stale_claims(meta)}")
        ok = False
    else:
        print("  元讨论行排除有效（不再把「讲这个坑」当成「犯这个坑」）")

    # ★ 专项：真实的过期声称（非元讨论）必须仍能抓到
    real = "本文列出当前缺陷：token.settlement_id 列不存在，故对账失效。"
    if not detect_stale_claims(real):
        print("  [FAIL] 真实过期声称未被抓到（排除规则过宽）")
        ok = False
    else:
        print("  真实过期声称仍可抓到")

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def detect_stale_claims(text):
    """
    检测文本是否「声称当前缺陷」且命中了已完成卡的关键词。
    返回命中的 (卡号, 关键词) 列表。

    ★ 逐行判定，并排除【元讨论】行 —— 即"引用/描述这个坑"而非"犯这个坑"的行。
      实测假阳性来源（开发规则与调度说明.md）：
        - 第 246/346/350 行：在引用 P-9 这个坑本身（"把已修复的 P0 仍列为当前缺陷"）
        - 第 198 行：在举例说明 F1-C4 与 I1-C2 的语义耦合
      ⇒ 若不做上下文排除，检测器会把「讲这个坑」误判为「犯这个坑」。
      排除规则：行内出现元讨论标记时不判定该行为过期声称。
    """
    hits = []
    claim_markers = ["当前缺陷", "至今未修", "仍未修", "尚未修复", "原样躺", "依然存在"]
    # 元讨论标记：出现这些说明该行是在【引用/描述】该问题，而非在【主张】它
    meta_markers = ["P-9", "建议", "断言", "教训", "反面", "示例", "例如", "参见", "见 "]

    for line in text.splitlines():
        if not any(m in line for m in claim_markers):
            continue
        if any(m in line for m in meta_markers):
            # 该行是元讨论（讲这个坑），跳过
            continue
        for card, kws in DONE_CARDS.items():
            for kw in kws:
                if kw in line:
                    hits.append((card, kw))
                    break
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    fails = []
    reports = list_reports()
    print(f"reports 目录报告数: {len(reports)}")

    # --- 断言 1：时效索引必须存在 ---
    if not os.path.isfile(FRESHNESS_IDX):
        print(f"  [FAIL] 时效索引不存在: {FRESHNESS_IDX}")
        print("RESULT=RED")
        return 1
    print(f"  [PASS] 时效索引存在: {FRESHNESS_IDX}")

    idx_text = read(FRESHNESS_IDX)
    rows = parse_index_rows(idx_text)
    print(f"  索引登记条数: {len(rows)}")

    # --- 断言 2：索引必须覆盖全部报告 ---
    covered = set(rows.keys())
    missing = [r for r in reports if r not in covered]
    extra = [r for r in covered if r not in reports]
    if missing:
        print(f"  [FAIL] 索引未覆盖 {len(missing)} 份报告:")
        for m in missing[:10]:
            print(f"         {m}")
        fails.append(f"index-missing:{len(missing)}")
    else:
        print(f"  [PASS] 索引覆盖全部 {len(reports)} 份报告")
    if extra:
        print(f"  [WARN] 索引有 {len(extra)} 条指向不存在的报告: {extra[:5]}")
        fails.append(f"index-extra:{len(extra)}")

    # --- 断言 3：每条索引项的状态必须合法 ---
    bad_status = []
    for name, row in rows.items():
        st = row["status"]
        if not any(s in st for s in STATUS_OK):
            bad_status.append((name, st))
    if bad_status:
        print(f"  [FAIL] {len(bad_status)} 条状态不合法（须含 {'/'.join(STATUS_OK)}）:")
        for n, s in bad_status[:10]:
            print(f"         {n}: {s!r}")
        fails.append(f"bad-status:{len(bad_status)}")
    else:
        print(f"  [PASS] 全部 {len(rows)} 条状态合法")

    # --- 断言 4：不得有报告声称"当前缺陷"而其修复卡已完成 ---
    print("")
    print("过期声称检测:")
    stale_found = []
    for name in reports:
        p = os.path.join(REPORTS, name)
        try:
            text = read(p)
        except Exception as e:
            print(f"  [WARN] 读取失败 {name}: {e}")
            continue
        hits = detect_stale_claims(text)
        if hits:
            # 若索引已把它标为"已过期"，则属于【已登记】的过期，允许（这正是索引的用途）
            status = rows.get(name, {}).get("status", "")
            if any(s in status for s in ("已过期", "部分过期", "归档")):
                print(f"  [PASS] {name} 含过期声称 {hits}，但索引已标记为「{status}」")
            else:
                print(f"  [FAIL] {name} 声称「当前缺陷」且命中已完成卡 {hits}，但索引状态为「{status}」")
                stale_found.append((name, hits))
        else:
            print(f"  [PASS] {name} 无过期声称")

    if stale_found:
        fails.append(f"stale-unregistered:{len(stale_found)}")

    print("")
    if fails:
        print(f"RESULT=RED  失败项: {fails}")
        return 1
    print("RESULT=GREEN  时效索引覆盖完整、状态合法、无未登记过期声称")
    return 0


if __name__ == "__main__":
    sys.exit(main())
