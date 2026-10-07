# -*- coding: utf-8 -*-
"""补齐 文档时效索引.md 的全部未覆盖项（含本提示词 + 并行会话产物）。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os

REPORTS = USDT_ROOT + r"\09-docs\reports"
IDX = os.path.join(REPORTS, "文档时效索引.md")

s = io.open(IDX, encoding="utf-8", errors="replace").read()

actual = set(f for f in os.listdir(REPORTS)
             if f.endswith(".md") and f != "文档时效索引.md")
covered = set()
for l in s.splitlines():
    if l.strip().startswith("|"):
        cells = [c.strip() for c in l.strip("|").split("|")]
        if cells and cells[0].strip("`* ").endswith(".md"):
            covered.add(cells[0].strip("`* "))

missing = sorted(actual - covered)
print("  reports 实际: %d" % len(actual))
print("  未覆盖: %d" % len(missing))
for m in missing:
    print("    %s" % m)

if not missing:
    print("  （无需登记）")
    raise SystemExit

rows = []
for m in missing:
    if "承接版" in m:
        note = "**有效**（上一轮总调度的交接提示词，自包含）"
    else:
        note = "**有效**（并行会话产出，2026-10-03）"
    rows.append("| `%s` | 2026-10-03 | 0 | %s |" % (m, note))

lines = s.splitlines()
# 找到主表的最后一行（以 | `xxx.md` 开头），在其后插入
last_idx = None
for i, l in enumerate(lines):
    if l.strip().startswith("| `") and l.strip().endswith("|"):
        last_idx = i

if last_idx is None:
    print("  ★ 未找到表尾")
    raise SystemExit

out = lines[:last_idx + 1] + rows + lines[last_idx + 1:]
io.open(IDX, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("  ✅ 已登记 %d 行（插入于第 %d 行后）" % (len(rows), last_idx + 1))
