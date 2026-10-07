import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

sql = QIANKE_SRC + r'\qianke\qianke0301.sql'
s = open(sql, encoding='utf-8', errors='replace').read()

# 1) 确认 machine / wallet 的完整 DDL（用于写 ALTER 语句）
for tbl in ['machine', 'wallet']:
    m = re.search(r'CREATE TABLE\s+`%s`\s*\(' % tbl, s, re.I)
    i = s.index('(', m.start())
    depth = 0
    for j in range(i, len(s)):
        if s[j] == '(':
            depth += 1
        elif s[j] == ')':
            depth -= 1
            if depth == 0:
                end = j
                break
    # 取到 ENGINE 结束
    tail = s[end: s.find(';', end) + 1]
    print('=' * 78)
    print('CREATE TABLE `%s`' % tbl)
    print('=' * 78)
    print(s[m.start(): s.find(';', end) + 1])
    print()

# 2) 现有 app 路由
r = QIANKE_SRC + r'\qianke\router\app\public.go'
print('=' * 78)
print('router/app/public.go 全文')
print('=' * 78)
print(open(r, encoding='utf-8', errors='replace').read())
