# -*- coding: utf-8 -*-
"""把三脚本的最终哈希写入判据脚本改动记录。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib
import io
import os

FIX = IOS_ROOT + r"\_integration\_fix_work"
DOC = USDT_ROOT + r"\09-docs\reports\判据脚本改动记录_20261003.md"

files = ["verify_entries_coruna.mjs",
         "verify_i1c2_darksword_entries.mjs",
         "verify_i1c2_runtime.mjs"]

rows = []
for f in files:
    p = os.path.join(FIX, f)
    raw = open(p, "rb").read()
    rows.append("| `%s` | `%s` | %d |" % (f, hashlib.sha256(raw).hexdigest(), len(raw)))

s = io.open(DOC, encoding="utf-8", errors="replace").read()

# 用正则替换 §六 的三个占位行
import re
pat = re.compile(r"\| \*\*`verify_entries_coruna\.mjs`\*\* \|[^\n]*\n"
                 r"\| \*\*`verify_i1c2_darksword_entries\.mjs`\*\* \|[^\n]*\n"
                 r"\| \*\*`verify_i1c2_runtime\.mjs`\*\* \|[^\n]*")
new_block = "\n".join(rows)
s2, cnt = pat.subn(new_block, s, count=1)

if cnt == 0:
    print("  ★ 未匹配占位块，改为在 §六 表头后插入")
    # 退化：在 "## 六 · 最终哈希" 之后的第一个表格行后插入
    idx = s.find("## 六 · 最终哈希")
    if idx > 0:
        # 找该段的第一行 '|'
        seg = s[idx:]
        lines = seg.splitlines()
        out = []
        inserted = False
        for l in lines:
            out.append(l)
            if not inserted and l.strip().startswith("|---"):
                out.extend(rows)
                inserted = True
        s2 = s[:idx] + "\n".join(out)
        cnt = 1 if inserted else 0

if cnt:
    io.open(DOC, "w", encoding="utf-8", newline="\n").write(s2)
    print("  ✅ 已写入 %d 行哈希" % len(rows))
    for r in rows:
        print("    %s" % r)
else:
    print("  ★ 写入失败")
