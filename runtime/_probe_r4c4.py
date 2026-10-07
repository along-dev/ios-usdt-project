# -*- coding: utf-8 -*-
"""R4-C4 停靠点 3 核实：privesc_results.json 是否含真实凭据（决策 9 称"非凭据"）。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import json
import re

P = USDT_ROOT + r"\11-payment\privesc_results.json"
s = io.open(P, encoding="utf-8", errors="replace").read()

PATS = ["password", "passwd", "pwd", "token", "secret", "jwt",
        "apikey", "api_key", "Bearer", "private_key", "merchantKey",
        "signkey", "sign_key", "md5key"]

print("=== 凭据关键词扫描（0 命中即'非凭据'成立）===")
total = 0
for pat in PATS:
    n = len(re.findall(pat, s, re.I))
    total += n
    if n:
        print("  %-14s %d 次" % (pat, n))
if total == 0:
    print("  ★ 全部 0 命中 ⇒ 与决策 9 的『非凭据』一致")

print("")
print("=== JSON 结构（30 条）===")
d = json.loads(s)
print("  条数:", len(d))
keys = set()
for r in d:
    if isinstance(r, dict):
        keys |= set(r.keys())
print("  出现的键:", sorted(keys))

print("")
print("=== 前 3 条的 tag / path / status ===")
for i, r in enumerate(d[:3]):
    print("  [%d] tag=%s" % (i, str(r.get("tag"))[:60]))
    print("      path=%s status=%s" % (r.get("path"), r.get("status")))

print("")
print("=== 是否含疑似凭据的长串（>=32 位 hex/base64）===")
sus = re.findall(r"[A-Za-z0-9+/=_-]{32,}", s)
print("  长串数量:", len(sus))
for x in sus[:5]:
    print("   ", x[:60])
