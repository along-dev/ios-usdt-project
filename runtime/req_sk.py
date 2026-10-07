import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

fp = QIANKE_SRC + r'\qianke\blockchain\scan.go'
s = open(fp, encoding='utf-8', errors='replace').read()

m = re.search(r'^func\s+Sk\s*\(', s, re.M)
print('=' * 74)
print('func Sk 全文')
print('=' * 74)
if m:
    # 打印到下一个顶层 func
    rest = s[m.start():]
    nxt = re.search(r'\nfunc\s', rest[1:])
    seg = rest[:nxt.start() + 1] if nxt else rest
    print(seg)
else:
    print('NOT FOUND')
