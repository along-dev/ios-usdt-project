# -*- coding: utf-8 -*-
"""R3-C2 摸底 3：按 basename 全树搜索，评估"可核实比例"。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib
import io
import os
import re
from collections import Counter, defaultdict

ROOT = USDT_ROOT
MAN = os.path.join(ROOT, "_manifest.sha256")
lines = io.open(MAN, encoding="utf-8-sig", errors="replace").read().splitlines()

entries = []
for l in lines:
    s = l.strip()
    m = re.match(r"^([0-9a-fA-F]{64})\s+\*?(.+)$", s)
    if m:
        entries.append((m.group(1).lower(), m.group(2).strip()))
print("manifest 条数:", len(entries))

# 建全树 basename → [路径] 索引（跳过 node_modules / .git / 大目录）
SKIP = {"node_modules", ".git", ".vs", "__pycache__", "_toolchain", "_gopath", "_gocache",
        "_snap_before", "_review_baseline_20260929_1837"}
idx = defaultdict(list)
n_files = 0
for dp, dn, fns in os.walk(ROOT):
    dn[:] = [d for d in dn if d not in SKIP]
    for fn in fns:
        p = os.path.join(dp, fn)
        try:
            if os.path.getsize(p) > 20 * 1024 * 1024:
                continue
        except Exception:
            continue
        idx[fn].append(p)
        n_files += 1
print("现树文件数（已跳过 node_modules 等）:", n_files)
print("唯一 basename 数:", sum(1 for v in idx.values() if len(v) == 1))

# 统计
uniq = multi = missing = 0
ok = bad = 0
miss_list = []
bad_list = []
for h, rel in entries:
    base = os.path.basename(rel.replace("\\", os.sep))
    cands = idx.get(base, [])
    if not cands:
        missing += 1
        if len(miss_list) < 10:
            miss_list.append(rel)
        continue
    if len(cands) > 1:
        multi += 1
        continue
    uniq += 1
    p = cands[0]
    try:
        cur = hashlib.sha256(open(p, "rb").read()).hexdigest()
    except Exception:
        continue
    if cur == h:
        ok += 1
    else:
        bad += 1
        if len(bad_list) < 15:
            bad_list.append((rel, os.path.relpath(p, ROOT), h[:12], cur[:12]))

print("")
print("=== 分类 ===")
print("  唯一匹配:", uniq, " → 一致:", ok, " 不符:", bad)
print("  多义(basename 在树中出现多次):", multi)
print("  现树中缺失:", missing)
print("")
print("=== 不符样本（前 15）===")
for rel, p, h1, h2 in bad_list:
    print("  %-52s %s" % (rel[:52], p[:60]))
    print("      manifest=%s…  actual=%s…" % (h1, h2))
print("")
print("=== 缺失样本（前 10）===")
for x in miss_list:
    print("  ", x[:90])
