# -*- coding: utf-8 -*-
"""补登记 L049 到 文档时效索引.md。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io

p = USDT_ROOT + r"\09-docs\reports\文档时效索引.md"
s = io.open(p, encoding="utf-8", errors="replace").read()

if "L049" in s:
    print("  已含 L049，跳过")
    raise SystemExit

MARK = "| `L046/L047/L048`"
NEW_ROW = ("| `L049`（在 `ledger/`） | 2026-10-02 | 0 | **有效**（批次 2/3 收尾："
           "三方 BIND_HOST 能力改造 / t22 静默兜底修复 / `X:` 依赖消除） |")

lines = s.splitlines()
out = []
ins = False
for l in lines:
    out.append(l)
    if not ins and l.strip().startswith(MARK):
        out.append(NEW_ROW)
        ins = True

if ins:
    io.open(p, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    print("  ✅ 已登记 L049")
else:
    print("  ★ 未找到插入点，列出相关行：")
    for i, l in enumerate(lines, 1):
        if "L046" in l or "L047" in l or "L048" in l:
            print("    %4d: %s" % (i, l[:110]))
