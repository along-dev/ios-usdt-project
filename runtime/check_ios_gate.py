import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

# 1) SUPPORTED_IOS.md
p = IOS_ROOT + r'\ios15-17版本漏洞\ios15-17版本漏洞\coruna\SUPPORTED_IOS.md'
print('=== SUPPORTED_IOS.md exists=', os.path.isfile(p), 'size=', os.path.getsize(p) if os.path.isfile(p) else -1)
if os.path.isfile(p):
    print(open(p, encoding='utf-8', errors='replace').read()[:2500])

# 2) locate expires.html gate
print()
print('=== expires.html search ===')
for root in [IOS_ROOT + r'\_analysis', IOS_ROOT + r'\ios-xy-main', IOS_ROOT + r'\_integration']:
    if not os.path.isdir(root):
        continue
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if 'expires' in f.lower():
                print('  ', os.path.join(dp, f))
