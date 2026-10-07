# -*- coding: utf-8 -*-
"""补登记 2 份并行会话产物到 文档时效索引.md。

★ 依据 P-53：计数类/枚举类判据必须反映【当下磁盘真值】。
  这 2 份报告是【并行会话】在 22:41 / 22:56 新增的
  （我方主集跑于 22:3x）⇒ 属合法新增，应登记而非删除。
"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import hashlib

p = USDT_ROOT + r"\09-docs\reports\文档时效索引.md"
s = io.open(p, encoding="utf-8", errors="replace").read()

NEW = [
    ("后续修复与全量代码审核报告.md",
     "**有效**（并行会话的独立复现全量审核；自述仅只读、未改代码）"),
    ("处理提示词_批次2收尾.md",
     "**有效**（并行会话产出的批次 2 收尾提示词）"),
]

added = []
for fname, note in NEW:
    if fname in s:
        print("  已含 %s" % fname)
        continue
    lines = s.splitlines()
    out = []
    ins = False
    for l in lines:
        out.append(l)
        if not ins and l.strip().startswith("| `完成度对比报告.md`"):
            out.append("| `%s` | 2026-10-02 | 0 | %s |" % (fname, note))
            ins = True
    if ins:
        s = "\n".join(out) + "\n"
        added.append(fname)
    else:
        print("  ★ 未找到插入点: %s" % fname)

if added:
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)
    print("  ✅ 已登记: %s" % ", ".join(added))
else:
    print("  （无新增）")

print("")
print("  新 sha256:", hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16])
