# -*- coding: utf-8 -*-
"""T15 取证：P2-4（WalletData/device-event 30 天 TTL 未纳入设计）+ 波次 4 的其余项。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re

ROOT = USDT_ROOT

print("=== 1) P2-4 的原文（需求文档）===")
p = os.path.join(ROOT, "09-docs", "analysis", "需求文档.md")
lines = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
for i, l in enumerate(lines, 1):
    if "P2-4" in l or "TTL" in l or "30 天" in l or "30天" in l:
        print("  %4d: %s" % (i, l.strip()[:150]))

print("")
print("=== 2) P2-7 的原文 ===")
for i, l in enumerate(lines, 1):
    if "P2-7" in l or "多副本" in l:
        print("  %4d: %s" % (i, l.strip()[:150]))

print("")
print("=== 3) 代码中的 TTL / expireAfterSeconds ===")
for base in [os.path.join(ROOT, "02-backend-node", "src_restored")]:
    for dp, dn, fns in os.walk(base):
        dn[:] = [d for d in dn if d not in ("node_modules", ".git")]
        for fn in fns:
            if not fn.endswith(".js"):
                continue
            fp = os.path.join(dp, fn)
            try:
                s = io.open(fp, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            if "expireAfterSeconds" in s or "expires:" in s or "TTL" in s:
                rel = os.path.relpath(fp, ROOT)
                for i, l in enumerate(s.splitlines(), 1):
                    if any(k in l for k in ("expireAfterSeconds", "expires:", "TTL", "30 * 24", "2592000")):
                        print("  %s:%d  %s" % (rel, i, l.strip()[:120]))

print("")
print("=== 4) WalletData / device-event 的模型定义 ===")
PAT = re.compile(r"WalletData|device-event|deviceEvent")
for dp, dn, fns in os.walk(os.path.join(ROOT, "02-backend-node", "src_restored")):
    dn[:] = [d for d in dn if d not in ("node_modules", ".git")]
    for fn in fns:
        if not fn.endswith(".js"):
            continue
        fp = os.path.join(dp, fn)
        try:
            s = io.open(fp, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if PAT.search(s):
            rel = os.path.relpath(fp, ROOT)
            n = len(PAT.findall(s))
            print("  %-70s %d 命中" % (rel, n))
