import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

sql = QIANKE_SRC + r'\qianke\qianke0301.sql'
s = open(sql, encoding='utf-8', errors='replace').read()
lines = s.split('\n')

# 取几条 wallet INSERT（原文，只看结构不打印助记词）
print('=== wallet INSERT 结构（列顺序）===')
i = s.find('CREATE TABLE `wallet`')
seg = s[i:i+2500]
cols = re.findall(r'^\s*`([a-z_0-9]+)`', seg, re.M)
print('列顺序:', cols)
print()

ins = [l for l in lines if l.startswith('INSERT INTO `wallet`')]
print('wallet INSERT 条数:', len(ins))
# 只打印字段个数与 type 值，避免助记词/私钥外泄
for l in ins[:6]:
    m = re.search(r"VALUES\s*\((.*)\);?\s*$", l)
    if not m:
        continue
    # 简易 CSV 切分（考虑引号）
    body = m.group(1)
    parts = re.findall(r"'(?:[^'\\]|\\.)*'|[^,]+", body)
    vals = [p.strip() for p in parts]
    print('  字段数=%d  type=%s  wallet_name=%s  region=%s' % (
        len(vals), vals[3] if len(vals) > 3 else '?',
        vals[2] if len(vals) > 2 else '?', vals[10] if len(vals) > 10 else '?'))
