# -*- coding: utf-8 -*-
"""查看 文档时效索引.md 的主表结构与末行，供补入新报告。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io

p = USDT_ROOT + r"\09-docs\reports\文档时效索引.md"
lines = io.open(p, encoding="utf-8", errors="replace").read().splitlines()

print("  总行数:", len(lines))
print("")
print("=== 含 .md 的表格行 ===")
rows = []
for i, l in enumerate(lines, 1):
    if l.strip().startswith("|"):
        cells = [c.strip() for c in l.strip("|").split("|")]
        if cells and cells[0].strip("`* ").endswith(".md"):
            rows.append((i, l))
print("  条数:", len(rows))
for i, l in rows[:6]:
    print("  %4d: %s" % (i, l.rstrip()[:118]))
print("  ...")
for i, l in rows[-6:]:
    print("  %4d: %s" % (i, l.rstrip()[:118]))

print("")
print("=== 第 14-30 行（看表头）===")
for i in range(13, min(32, len(lines))):
    print("  %4d: %s" % (i + 1, lines[i].rstrip()[:118]))
