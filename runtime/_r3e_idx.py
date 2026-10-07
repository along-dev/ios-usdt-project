# -*- coding: utf-8 -*-
"""补 文档时效索引.md 的 §2.2b 表，加入 L048 台账说明行。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io

p = USDT_ROOT + r"\09-docs\reports\文档时效索引.md"
s = io.open(p, encoding="utf-8", errors="replace").read()

if "L048" in s:
    print("  已含 L048，跳过")
    raise SystemExit

MARK = "| `完成度对比报告.md`"
lines = s.splitlines()
out = []
ins = False
for l in lines:
    out.append(l)
    if not ins and l.strip().startswith(MARK):
        out.append(
            "| `L046/L047/L048`（在 `ledger/`） | 2026-10-02 | 0 | "
            "**有效**（批次 1/2/3 收口台账；L048 含决策 Agent 流程与构建集不跑裁定） |"
        )
        ins = True

if ins:
    io.open(p, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    print("  ✅ 已补 L046/L047/L048 行")
else:
    print("  ★ 未找到插入点，列出含「完成度对比」的行：")
    for i, l in enumerate(lines, 1):
        if "完成度对比" in l:
            print("    %4d: %s" % (i, l[:110]))
