# -*- coding: utf-8 -*-
"""查重：对每个关键词，找出它落在哪条 E-<NN>，并打印该条标题＋命中行。"""
import io, re

L = r"C:\Users\pro9 i5 16 256\.claude\skills\agent-error-ledger\references\01-entries.md"
lines = io.open(L, encoding="utf-8").read().splitlines()
cur = None
hits = {}
KEYS = ["计数≠清单", "计数与清单", "同族形态", "被测物", "normalizer", "规范",
        "断言先于", "先写结论", "先写", "卡面", "升级", "重派"]
for i, ln in enumerate(lines, 1):
    m = re.match(r"^## (E-\d+)\s*(.*)", ln)
    if m:
        cur = (m.group(1), m.group(2)[:60])
        continue
    for k in KEYS:
        if k in ln:
            hits.setdefault(k, []).append((cur, i, ln.strip()[:110]))

for k in KEYS:
    hs = hits.get(k) or []
    print("== %s ：%d 处 ==" % (k, len(hs)))
    seen = set()
    for cur, i, t in hs[:6]:
        tag = cur[0] if cur else "?"
        if tag in seen:
            continue
        seen.add(tag)
        print("   %s %-58s ← L%d" % (tag, (cur[1] if cur else ""), i))
        print("        %s" % t)
    print()
