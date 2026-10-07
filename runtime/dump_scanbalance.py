import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

base = QIANKE_SRC + r'\qianke'
fp = os.path.join(base, 'blockchain', 'scan.go')
s = open(fp, encoding='utf-8', errors='replace').read()

print('=== ScanBalance 函数体（前 2600 字符）===')
i = s.find('func ScanBalance')
print(s[i:i + 2600])
