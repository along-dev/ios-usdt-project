# -*- coding: utf-8 -*-
"""从 admin_dashboard.html 提取 D1 端点的真实调用形态（只读取证）。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import re

H = USDT_ROOT + r"\03-web-admin\static\admin_dashboard.html"
src = open(H, encoding="utf-8", errors="replace").read()

print("=== 1. theme 取值 ===")
themes = sorted(set(re.findall(r'data-theme="([a-z]+)"', src)))
print("  ", themes)

print("\n=== 2. 全部 fetch 调用（端点 + 方法）===")
# 匹配 fetch(...)  并取后续 300 字符看有无 method
calls = []
for m in re.finditer(r"fetch\(\s*(?:ADMIN\s*\+\s*)?[`'\"]([^`'\"]*)[`'\"]", src):
    line_no = src[:m.start()].count("\n") + 1
    tail = src[m.start():m.start() + 300]
    meth = "GET"
    mm = re.search(r'method:\s*[\'"]([A-Z]+)[\'"]', tail)
    if mm:
        meth = mm.group(1)
    calls.append((line_no, meth, m.group(1)))

for ln, meth, path in calls:
    print(f"  :{ln:<5} {meth:<5} {path}")

print("\n=== 3. 去重后的端点集合 ===")
uniq = sorted(set((m, p) for _l, m, p in calls))
for m, p in uniq:
    print(f"  {m:<5} {p}")

print("\n=== 4. switchTheme 的实现（看 setTheme 如何调后端）===")
i = src.find("function switchTheme")
if i < 0:
    i = src.find("switchTheme =")
if i >= 0:
    print(src[i:i + 700])
else:
    print("  未找到 switchTheme 定义")

print("\n=== 5. theme 相关的 fetch（若有）===")
for m in re.finditer(r".{0,80}theme.{0,120}", src, re.I):
    s = m.group(0).replace("\n", " ")
    if "fetch" in s or "ADMIN" in s:
        print("  ", s.strip()[:200])
