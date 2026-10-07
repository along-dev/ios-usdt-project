# -*- coding: utf-8 -*-
"""修复清单 11/13 的重复前缀（上一次正则替换的副作用）。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import re

p = USDT_ROOT + r"\09-docs\reports\上线加固清单.md"
s = io.open(p, encoding="utf-8", errors="replace").read()

# 修 `| 11 | | 11 | ...` → `| 11 | ...`
before = len(re.findall(r"\|\s*(\d+)\s*\|\s*\|\s*(\d+)\s*\|", s))
s = re.sub(r"\|\s*(\d+)\s*\|\s*\|\s*(\d+)\s*\|", r"| \1 |", s)

io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("  修复重复前缀: %d 处" % before)

# 复查
s2 = io.open(p, encoding="utf-8", errors="replace").read()
print("")
print("  复查 11/13 行：")
for l in s2.splitlines():
    t = l.strip()
    if t.startswith("| 11 |") or t.startswith("| 13 |") or t.startswith("| 3 |") or t.startswith("| 8 |") or t.startswith("| 10 |"):
        print("    %s" % t[:130])
print("")
print("  残留 `| |`: %d" % len(re.findall(r"\|\s*\|\s*\|", s2)))
