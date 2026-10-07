import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import re

s = open(QIANKE_SRC + r'\qianke\qianke0301.sql', encoding='utf-8', errors='replace').read()

# 逐条解析 sys_base_menus 的 INSERT，取 hidden 字段（第 9 个，index 8）
pat = re.compile(r"INSERT INTO `sys_base_menus` VALUES \((.*?)\);", re.S)
for m in pat.finditer(s):
    body = m.group(1)
    # 简单 CSV 切分（考虑单引号）
    parts = re.findall(r"'(?:[^'\\]|\\.)*'|[^,]+", body)
    parts = [p.strip() for p in parts]
    if len(parts) < 9:
        continue
    mid = parts[0]
    name = parts[7].strip("'")
    hidden = parts[8]
    try:
        mid_i = int(mid)
    except ValueError:
        continue
    if mid_i in (2, 9, 14, 22, 1, 8):
        print('id=%-4s name=%-34s hidden=%s' % (mid, name[:34], hidden))
