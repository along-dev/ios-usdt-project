import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import re

sql = QIANKE_SRC + r'\qianke\qianke0301.sql'
s = open(sql, encoding='utf-8', errors='replace').read()


def cols(tbl):
    m = re.search(r'CREATE TABLE\s+`%s`\s*\(' % tbl, s)
    if not m:
        return None
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
    return re.findall(r'^\s*`([a-z_0-9]+)`', body, re.M)


for t in ['sys_dictionaries', 'sys_dictionary_details', 'sys_base_menu_parameters']:
    c = cols(t)
    print('=== %s ===' % t)
    print('   列:', c)
    # 打印几条数据
    ins = re.findall(r'INSERT INTO `%s` VALUES \((.{0,200})' % t, s)
    for x in ins[:3]:
        print('   样本:', x[:160])
    print()
