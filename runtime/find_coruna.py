import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re, sys

roots = [
    IOS_ROOT + r'\ios15-17版本漏洞\ios15-17版本漏洞\coruna',
    IOS_ROOT + r'\_analysis',
]
for r in roots:
    print('===', r, 'exists=', os.path.isdir(r))
    if not os.path.isdir(r):
        continue
    n = 0
    for dp, dn, fn in os.walk(r):
        for f in fn:
            if re.search(r'platform|coruna|version', f, re.I):
                n += 1
                if n <= 40:
                    print('   ', os.path.join(dp, f)[len(r):])
    print('   total matches:', n)
