# -*- coding: utf-8 -*-
"""R3-C2 摸底 2：找 manifest 的根映射（相对路径相对于哪个根）。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re
from collections import Counter

ROOT = USDT_ROOT
MAN = os.path.join(ROOT, "_manifest.sha256")
lines = io.open(MAN, encoding="utf-8-sig", errors="replace").read().splitlines()

entries = []
for l in lines:
    s = l.strip()
    m = re.match(r"^([0-9a-fA-F]{64})\s+\*?(.+)$", s)
    if m:
        entries.append((m.group(1).lower(), m.group(2).strip()))
print("解析出 %d 条" % len(entries))

# 候选根
CANDS = [
    ("(ROOT)", ROOT),
    ("02-backend-node", os.path.join(ROOT, "02-backend-node")),
    ("02-backend-node/src", os.path.join(ROOT, "02-backend-node", "src")),
    ("02-backend-node/src_restored", os.path.join(ROOT, "02-backend-node", "src_restored")),
    ("01-backend-go", os.path.join(ROOT, "01-backend-go")),
    ("03-web-admin", os.path.join(ROOT, "03-web-admin")),
    ("04-landing", os.path.join(ROOT, "04-landing")),
]

# 抽样 200 条，看哪个根能命中
sample = entries[:400]
score = Counter()
for h, rel in sample:
    for name, base in CANDS:
        p = os.path.join(base, rel.replace("\\", os.sep))
        if os.path.isfile(p):
            score[name] += 1
print("")
print("=== 抽样 %d 条：各候选根的命中数 ===" % len(sample))
for k, v in score.most_common():
    print("  %-32s %d" % (k, v))

# 直接看几个样本在磁盘上哪里有
print("")
print("=== 5 个样本的磁盘定位 ===")
for h, rel in entries[:5]:
    print("  %s  (%s)" % (rel, h[:12]))
    found = False
    for name, base in CANDS:
        p = os.path.join(base, rel.replace("\\", os.sep))
        if os.path.isfile(p):
            print("      ⇒ %s" % name)
            found = True
    if not found:
        # 全树前 3 层搜
        base_name = os.path.basename(rel.replace("\\", os.sep))
        hits = []
        for r in (ROOT,):
            for dp, dn, fns in os.walk(r):
                dn[:] = [d for d in dn if d not in ("node_modules", ".git")]
                if len(os.path.relpath(dp, r).split(os.sep)) > 4:
                    dn[:] = []
                    continue
                if base_name in fns:
                    hits.append(os.path.relpath(os.path.join(dp, base_name), r))
        print("      ⇒ 未在候选根命中；全树浅搜: %s" % (hits[:3] if hits else "无"))
