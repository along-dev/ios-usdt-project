import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

# 1) SQL DDL 中三张表的真实列定义
sql = QIANKE_SRC + r'\qianke\qianke0301.sql'
s = open(sql, encoding='utf-8', errors='replace').read()
lines = s.split('\n')

for tbl in ['machine', 'wallet', 'bill', 'packet']:
    m = re.search(r'CREATE TABLE\s+`%s`\s*\(' % tbl, s, re.I)
    if not m:
        print('=== %s: NOT FOUND ===' % tbl); continue
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
    body = s[i:end + 1]
    cols = re.findall(r'^\s*`([a-z_0-9]+)`\s+([a-zA-Z]+(?:\([\d,]+\))?)', body, re.M)
    print('=== %s 列（%d）===' % (tbl, len(cols)))
    for c, t in cols:
        print('    %-22s %s' % (c, t))
    print()
