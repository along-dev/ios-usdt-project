# -*- coding: utf-8 -*-
"""读取 pjuyr 会话的最新内容（解压 zstd jsonl）。"""
import io
import json
import os

import zstandard as zstd

S = r"E:\CTF\dsh\sessions\--E-CTF-~4EFB~52A1-pjuyr--\session-d2b2a558-c7ca-4ad6-a05d-1ffeada8bb3c"
F = os.path.join(S, "session.v3.jsonl.zstd")

raw = open(F, "rb").read()
dctx = zstd.ZstdDecompressor()
txt = dctx.decompress(raw, max_output_size=200 * 1024 * 1024).decode("utf-8", "replace")
lines = [l for l in txt.splitlines() if l.strip()]
print("  解压后行数: %d" % len(lines))
print("  解压后大小: %d B" % len(txt))
print("")

recs = []
for l in lines:
    try:
        recs.append(json.loads(l))
    except Exception:
        pass
print("  可解析记录: %d" % len(recs))

# 探测字段结构
if recs:
    print("")
    print("  === 记录字段结构（取样）===")
    for k in sorted(recs[0].keys()):
        v = recs[0][k]
        print("    %-18s %s" % (k, type(v).__name__))

# 统计类型分布
from collections import Counter
c = Counter()
for r in recs:
    t = r.get("type") or r.get("role") or r.get("kind") or "?"
    c[t] += 1
print("")
print("  === 类型分布 ===")
for k, v in c.most_common(10):
    print("    %-20s %d" % (k, v))
