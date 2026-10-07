# ★ X3：本脚本【自带】UTF-8 输出，不依赖调用方设置 PYTHONIOENCODING（P-10）
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
import sys as _sys

_os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # 旧版 Python 无 reconfigure 时静默降级
import re, sys, json

p = IOS_ROOT + r'\ios15-17版本漏洞\ios15-17版本漏洞\coruna\platform_module.js'
s = open(p, encoding='utf-8', errors='replace').read()
print('file bytes:', len(s))
print('total lines:', s.count('\n') + 1)

# Locate the three table identifiers
for name in ['PSNMWj', 'LTgSl5', 'RoAZdq', 'GFx77t']:
    idx = [m.start() for m in re.finditer(re.escape(name), s)]
    print('%-8s occurrences: %d' % (name, len(idx)))

# Extract the minVersion values belonging to each table by scanning
# the region after each table name occurrence.
def region(name):
    out = []
    for m in re.finditer(re.escape(name), s):
        seg = s[m.start(): m.start() + 6000]
        out.append(seg)
    return out

for name in ['PSNMWj', 'LTgSl5', 'RoAZdq']:
    for i, seg in enumerate(region(name)):
        nums = re.findall(r'minVersion\s*[:=]\s*(\d+)', seg)
        if nums:
            iv = [int(x) for x in nums]
            print('%s[%d]: count=%d min=%d max=%d' % (name, i, len(iv), min(iv), max(iv)))
            print('     values:', sorted(set(iv))[-6:])

# Show the selection logic line
for m in re.finditer(r'.{0,120}GFx77t\s*>\s*\w+.{0,80}', s):
    print('SEL:', m.group(0).strip()[:200])
