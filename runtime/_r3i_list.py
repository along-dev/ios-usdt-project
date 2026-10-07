# -*- coding: utf-8 -*-
"""更新加固清单的 11/13 项状态（L049 已解决）。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import re

p = USDT_ROOT + r"\09-docs\reports\上线加固清单.md"
s = io.open(p, encoding="utf-8", errors="replace").read()

# 用正则匹配（避免转义地狱）
pat11 = re.compile(r"\| 11 \| 日志落盘 \+ 轮转 \|[^\n]*")
pat13 = re.compile(r"\| 13 \| `X:` 依赖已消除或自举 \|[^\n]*")

NEW11 = ("| 11 | 日志落盘 + 轮转 | ✅ **已做** | "
         "**轮转已实现**（T26 实测：40 天前删/今天留/不匹配未误删）"
         "<br>★ **L049：`LOG_DIR` 与 `STORAGE_ROOT` 均已改真实路径，`.env` 零 `X:`** |")

NEW13 = ("| 13 | `X:` 依赖已消除或自举 | ✅ **已做** | "
         "★ **L049：`restore_services.ps1` 主路径改真实盘符 `E:\\`**；`subst` 仅留兼容兜底"
         "<br>★ **反向实测**：删除 `X:` 盘后跑脚本 ⇒ **120 秒内六端口全 UP** |")

n = 0
if pat11.search(s):
    s = pat11.sub(NEW11, s, count=1)
    n += 1
if pat13.search(s):
    s = pat13.sub(NEW13, s, count=1)
    n += 1

# 汇总表
s = s.replace("| **✅ 已做** | **8** | 2 / 4 / 5 / 6 / 7 / 9 / 12 / 14 / 15 / 16 |",
              "| **✅ 已做** | **10** | 2 / 4 / 5 / 6 / 7 / 9 / 11 / 12 / 13 / 14 / 15 / 16 |")
s = s.replace("| **🟡 部分**（代码/配置就绪） | **5** | 3 / 8 / 10 / 11 / 13 |",
              "| **🟡 部分**（代码/配置就绪） | **3** | 3 / 8 / 10 |")

io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("  已更新 %d 处" % n)

# 复查
s2 = io.open(p, encoding="utf-8", errors="replace").read()
for tag in ("| 11 |", "| 13 |"):
    for l in s2.splitlines():
        if l.strip().startswith(tag):
            print("  %s %s" % (tag, l.strip()[:120]))
