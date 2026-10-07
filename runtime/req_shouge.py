import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

fp = QIANKE_SRC + r'\qianke\service\system\sys_qianke.go'
s = open(fp, encoding='utf-8', errors='replace').read()

for fn in ['ShouGe', 'Hf', 'Rk']:
    m = re.search(r'^func\s+(?:\([^)]*\)\s*)?%s\s*\(' % fn, s, re.M)
    if not m:
        print('NOT FOUND', fn); continue
    seg = s[m.start(): m.start() + 2200]
    print('=' * 74)
    print('func %s' % fn)
    print('=' * 74)
    print(seg)
    print()
