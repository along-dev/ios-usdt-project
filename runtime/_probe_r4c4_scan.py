# -*- coding: utf-8 -*-
"""R4-C4 取证：privesc_results.json 全 30 条的凭据扫描（消除停靠点 1）。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import json
import re

P = USDT_ROOT + r"\11-payment\privesc_results.json"
raw = io.open(P, encoding="utf-8", errors="replace").read()
d = json.loads(raw)

PATS = [
    ("AccessKey", r"AccessKey\"\s*:\s*\"([^\"]+)\""),
    ("SecretKey", r"SecretKey\"\s*:\s*\"([^\"]+)\""),
    ("password", r"password\"\s*:\s*\"([^\"]+)\""),
    ("token", r"[\"']?token[\"']?\s*:\s*\"([^\"]{8,})\""),
    ("Bearer", r"Bearer\s+([A-Za-z0-9_\-\.]{20,})"),
    ("jwt", r"(eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,})"),
]

print("=== 全 30 条的凭据扫描 ===")
found = {}
for name, pat in PATS:
    hits = []
    for m in re.finditer(pat, raw, re.I):
        hits.append(m.group(0)[:100])
    if hits:
        found[name] = hits

for name, hits in found.items():
    print("  %-12s %d 处" % (name, len(hits)))
    for h in hits[:4]:
        print("      %s" % h[:90])

if not found:
    print("  ✓ 无命中")

print("")
print("=== 逐条扫描（30 条，找含凭据的）===")
for i, r in enumerate(d):
    blob = json.dumps(r, ensure_ascii=False)
    flags = []
    for name, pat in PATS:
        if re.search(pat, blob, re.I):
            flags.append(name)
    if flags:
        print("  [%2d] tag=%-24s path=%-40s ★ %s"
              % (i, str(r.get("tag"))[:24], str(r.get("path"))[:40], ",".join(flags)))

print("")
print("=== 结构（供保形断言参考）===")
print("  条数:", len(d))
keys = set()
for r in d:
    if isinstance(r, dict):
        keys |= set(r.keys())
print("  键集合:", sorted(keys))
print("  CRLF 数:", raw.count("\r\n"), " LF 总数:", raw.count("\n"))
print("  首 2 字符:", repr(raw[:2]))
