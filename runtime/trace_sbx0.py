import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import re

p = IOS_ROOT + r'\ios15-17版本漏洞\ios15-17版本漏洞\darksword\sbx0_main_18.4.js'
s = open(p, encoding='utf-8', errors='replace').read()
lines = s.split('\n')
print('total lines:', len(lines))

# Every mention of sbx0_offsets with line number
for i, l in enumerate(lines):
    if 'sbx0_offsets' in l:
        # only show definition-ish or key-ish lines
        if re.search(r'sbx0_offsets\s*=', l) or re.search(r'^\s*"iPhone', l) or '_offsets' in l and 'var ' in l:
            print(i + 1, l.strip()[:150])
