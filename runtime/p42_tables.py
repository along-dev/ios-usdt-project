import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import re

sql = QIANKE_SRC + r'\qianke\qianke0301.sql'
s = open(sql, encoding='utf-8', errors='replace').read()

tables = re.findall(r'CREATE TABLE\s+`(\w+)`', s)
print('表总数:', len(tables))
for t in sorted(tables):
    print('  ', t)

print()
print('=== 是否存在 sys_params / 配置类表 ===')
for pat in ['sys_params', 'sys_config', 'config', 'params']:
    hit = [t for t in tables if pat in t.lower()]
    print('  %-14s -> %s' % (pat, hit or '无'))

print()
print('=== 版本信息 ===')
for m in re.finditer(r'.{0,40}(Server [Vv]ersion|MySQL).{0,60}', s):
    print('  ', m.group(0).strip()[:120])
    break
