# -*- coding: utf-8 -*-
"""R4-C4 停靠点 3 深查：secret / apikey / 40位hex 的上下文。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import json
import re

P = USDT_ROOT + r"\11-payment\privesc_results.json"
s = io.open(P, encoding="utf-8", errors="replace").read()

print("=== 1) 'secret' 的上下文（前后 120 字符）===")
for m in re.finditer(r"secret", s, re.I):
    a = max(0, m.start() - 120)
    b = min(len(s), m.end() + 120)
    print("  ...%s..." % s[a:b].replace("\n", " "))
    print("")

print("=== 2) 'apikey' 的上下文 ===")
for m in re.finditer(r"apikey", s, re.I):
    a = max(0, m.start() - 120)
    b = min(len(s), m.end() + 120)
    print("  ...%s..." % s[a:b].replace("\n", " "))
    print("")

print("=== 3) 40 位 hex 的上下文 ===")
for m in re.finditer(r"670aaaa1039cfe6ef25d48678acfe4a65816396b", s, re.I):
    a = max(0, m.start() - 150)
    b = min(len(s), m.end() + 150)
    print("  ...%s..." % s[a:b].replace("\n", " "))
    print("")

print("=== 4) 该 hex 出现在哪条记录 ===")
d = json.loads(s)
for i, r in enumerate(d):
    if isinstance(r, dict):
        blob = json.dumps(r, ensure_ascii=False)
        if "670aaaa1039cfe6ef25d48678acfe4a65816396b" in blob:
            print("  [%d] tag=%s" % (i, r.get("tag")))
            print("      path=%s" % r.get("path"))
            print("      resp 前 300: %s" % str(r.get("resp"))[:300])
