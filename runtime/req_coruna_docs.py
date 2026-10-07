import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os

V = IOS_ROOT + r'\ios15-17版本漏洞\ios15-17版本漏洞'

for rel in [r'coruna\README.md', r'coruna\ANALYSIS.md']:
    fp = os.path.join(V, rel)
    if os.path.isfile(fp):
        print('=' * 74)
        print(rel)
        print('=' * 74)
        print(open(fp, encoding='utf-8', errors='replace').read()[:3000])
        print()
