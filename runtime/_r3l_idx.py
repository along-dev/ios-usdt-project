# -*- coding: utf-8 -*-
"""补登记并行会话的 12 份报告（01:14-01:42 产出）到 文档时效索引.md。

★ 依据 P-53：计数类/枚举类判据必须反映【当下磁盘真值】。
  这些报告是【并行会话】新增的合法产物 ⇒ 应登记而非删除。
"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os

IDX = USDT_ROOT + r"\09-docs\reports\文档时效索引.md"
s = io.open(IDX, encoding="utf-8", errors="replace").read()

NEW = [
    ("三段业务面审核与等级设计.md", "**有效**（并行会话：三段业务面审核与等级设计）"),
    ("上线就绪度判定.md", "**有效**（并行会话：上线就绪度判定）"),
    ("代码漏洞审核.md", "**有效**（并行会话：代码漏洞审核）"),
    ("全项目审核提示词.md", "**有效**（并行会话：全项目审核提示词）"),
    ("后续开发策划_总纲.md", "**有效**（并行会话：后续开发策划总纲）"),
    ("提示词_后台线.md", "**有效**（并行会话：后台线提示词）"),
    ("提示词_安卓线.md", "**有效**（并行会话：安卓线提示词）"),
    ("提示词_广告线.md", "**有效**（并行会话：广告线提示词）"),
    ("提示词_总调度_修复与后续开发.md", "**有效**（并行会话：总调度提示词）"),
    ("提示词_苹果app线.md", "**有效**（并行会话：苹果 app 线提示词）"),
]

# 先探测还有哪些未覆盖（脚本报 12 份，上面只列了 10 个名字）
REPORTS = USDT_ROOT + r"\09-docs\reports"
actual = set(f for f in os.listdir(REPORTS) if f.endswith(".md") and f != "文档时效索引.md")
covered = set()
for l in s.splitlines():
    if l.strip().startswith("|"):
        cells = [c.strip() for c in l.strip("|").split("|")]
        if cells and cells[0].strip("`* ").endswith(".md"):
            covered.add(cells[0].strip("`* "))
missing = sorted(actual - covered)
print("  实际未覆盖: %d 份" % len(missing))
for m in missing:
    print("    %s" % m)

# 补齐 NEW（用 missing 的真实名单，而非我硬编码的）
rows = []
for m in missing:
    note = "**有效**（并行会话产出，2026-10-02/03）"
    for n, d in NEW:
        if n == m:
            note = d
            break
    rows.append("| `%s` | 2026-10-03 | 0 | %s |" % (m, note))

if not rows:
    print("  （无需登记）")
    raise SystemExit

lines = s.splitlines()
out = []
ins = False
for l in lines:
    out.append(l)
    if not ins and l.strip().startswith("| `L049`"):
        out.extend(rows)
        ins = True

if ins:
    io.open(IDX, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    print("  ✅ 已登记 %d 行" % len(rows))
else:
    print("  ★ 未找到插入点")
