# -*- coding: utf-8 -*-
"""把 pjuyr-malware 目录登记入 文档时效索引.md。

★ doc_freshness 的 list_reports() 只枚举 reports/*.md
  ⇒ analysis/ 下的文件【不在该判据范围】。
  但为可发现性，仍在索引里加一行【说明性登记】。
"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os

IDX = USDT_ROOT + r"\09-docs\reports\文档时效索引.md"
s = io.open(IDX, encoding="utf-8", errors="replace").read()

MARK = "pjuyr 恶意分发体系"
if MARK in s:
    print("  已登记，跳过")
    raise SystemExit

ROW = ("| `analysis/pjuyr-malware/`（7 份报告） | 2026-10-03 | 0 | "
       "**有效**（**pjuyr 恶意分发体系分析归档**：IOC/滥用上报 + Android RAT 逆向 + "
       "iOS 投递方案 + 资源复刻；★ **样本哈希经总调度独立复核 2/2 一致**） |")

lines = s.splitlines()
# 插到主表末尾（最后一个以 | ` 开头的行之后）
last = None
for i, l in enumerate(lines):
    if l.strip().startswith("| `") and l.strip().endswith("|"):
        last = i

if last is None:
    print("  ★ 未找到表尾")
    raise SystemExit

out = lines[:last + 1] + [ROW] + lines[last + 1:]
io.open(IDX, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("  ✅ 已登记（插入于第 %d 行后）" % (last + 1))

# 顺带：把 INDEX.md 也加一段
IDX2 = USDT_ROOT + r"\09-docs\INDEX.md"
s2 = io.open(IDX2, encoding="utf-8", errors="replace").read()
if MARK not in s2:
    MARK2 = "### 3.3 早期分析"
    ADD = ("### 3.2c ★ pjuyr 恶意分发体系分析归档（2026-10-03）\n\n"
           "| 位置 | 内容 |\n|---|---|\n"
           "| `analysis/pjuyr-malware/` | **7 份报告**：IOC 清单/滥用上报、Android RAT 逆向、"
           "`ads.txt` 编码分析、iOS 投递方案、资源复刻、APK 获取记录；**含 README 索引 + 我方独立复核** |\n\n")
    if MARK2 in s2:
        s2 = s2.replace(MARK2, ADD + MARK2, 1)
        io.open(IDX2, "w", encoding="utf-8", newline="\n").write(s2)
        print("  ✅ INDEX.md 已补 §3.2c")
    else:
        print("  ★ INDEX.md 未找到插入锚点")
else:
    print("  INDEX.md 已含")
