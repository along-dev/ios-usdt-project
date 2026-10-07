import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

fp = IOS_ROOT + r'\ios15-17版本漏洞\ios15-17版本漏洞\coruna\index.html'
s = open(fp, encoding='utf-8', errors='replace').read()

i = s.find('DEVICE_VERSIONS')
print('=' * 76)
print('DEVICE_VERSIONS 上下文（前后 3000 字符）')
print('=' * 76)
print(s[max(0, i - 2000): i + 2500])
