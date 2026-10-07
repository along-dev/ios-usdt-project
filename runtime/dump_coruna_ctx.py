import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import re

p = IOS_ROOT + r'\ios15-17版本漏洞\ios15-17版本漏洞\coruna\platform_module.js'
s = open(p, encoding='utf-8', errors='replace').read()

# Print the context of the FIRST occurrence of each identifier
for name in ['PSNMWj', 'LTgSl5', 'RoAZdq']:
    m = re.search(re.escape(name), s)
    if m:
        st = max(0, m.start() - 300)
        print('=' * 30, name, 'first occurrence at offset', m.start())
        print(s[st: m.start() + 1400])
        print()
        break
