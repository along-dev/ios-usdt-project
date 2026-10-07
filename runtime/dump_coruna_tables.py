import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import re

p = IOS_ROOT + r'\ios15-17版本漏洞\ios15-17版本漏洞\coruna\platform_module.js'
s = open(p, encoding='utf-8', errors='replace').read()

# Find assignments of the runtime tables: PSNMWj = [ ... ]
for name in ['PSNMWj', 'LTgSl5', 'RoAZdq']:
    for m in re.finditer(re.escape(name) + r'\s*[:=]\s*\[', s):
        seg = s[m.start(): m.start() + 4000]
        # find matching close bracket naively at first "\n  ]" pattern
        print('=' * 25, name, 'assignment at offset', m.start())
        print(seg[:1500])
        print('...')
        # extract all numeric literals that look like versions (6-digit 1xxxxx)
        vers = re.findall(r'\b(1[0-9]{5})\b', seg)
        if vers:
            iv = sorted(set(int(v) for v in vers))
            print('  version-like numbers:', iv)
        print()
