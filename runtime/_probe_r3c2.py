# -*- coding: utf-8 -*-
"""R3-C2 摸底：_manifest.sha256 的规模 + 抽样核实（供写判据参考）。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib
import io
import os

ROOT = USDT_ROOT
MAN = os.path.join(ROOT, "_manifest.sha256")

print("=== manifest 基本信息 ===")
print("  bytes:", os.path.getsize(MAN))
raw = open(MAN, "rb").read()
print("  CRLF:", raw.count(b"\r\n"), " LF:", raw.count(b"\n"))
print("  首 3 字节:", raw[:3])

lines = io.open(MAN, encoding="utf-8", errors="replace").read().splitlines()
print("  行数:", len(lines))
print("")
print("=== 前 5 行 ===")
for l in lines[:5]:
    print("   ", l[:140])
print("")
print("=== 后 3 行 ===")
for l in lines[-3:]:
    print("   ", l[:140])

# 解析格式
import re
m = re.match(r"^([0-9a-fA-F]{64})\s+\*?(.+)$", lines[0].strip())
print("")
print("  格式样例解析:", "OK" if m else "★ 未识别")
if m:
    print("    sha:", m.group(1)[:16], "…")
    print("    path:", m.group(2)[:100])

# 统计路径前缀分布
from collections import Counter
c = Counter()
bad = 0
for l in lines:
    s = l.strip()
    if not s:
        continue
    mm = re.match(r"^([0-9a-fA-F]{64})\s+\*?(.+)$", s)
    if not mm:
        bad += 1
        continue
    p = mm.group(2).replace("\\", "/")
    c[p.split("/")[0] if "/" in p else "(root)"] += 1
print("")
print("=== 路径首段分布（前 15）===")
for k, v in c.most_common(15):
    print("  %-32s %d" % (k, v))
print("  无法解析的行:", bad)
