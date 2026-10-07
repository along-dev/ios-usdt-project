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
import re

p = IOS_ROOT + r'\ios15-17版本漏洞\ios15-17版本漏洞\darksword\rce_module.js'
s = open(p, encoding='utf-8', errors='replace').read()

m = re.search(r'const linkedit_to_device\s*=\s*\{', s)
i = s.index('{', m.end() - 1)
depth = 0
for j in range(i, len(s)):
    if s[j] == '{':
        depth += 1
    elif s[j] == '}':
        depth -= 1
        if depth == 0:
            end = j
            break
body = s[i:end + 1]

# Top-level version keys of linkedit_to_device
vkeys = re.findall(r"'(1[0-9],[0-9](?:,[0-9])?)'\s*:\s*\{", body)
print('linkedit_to_device version keys:', vkeys)
print('count:', len(vkeys))

# Build set per version key
for vk in vkeys:
    mm = re.search(r"'%s'\s*:\s*\{" % re.escape(vk), body)
    st = body.index('{', mm.end() - 1)
    d = 0
    for j in range(st, len(body)):
        if body[j] == '{':
            d += 1
        elif body[j] == '}':
            d -= 1
            if d == 0:
                e = j
                break
    seg = body[st:e + 1]
    vals = re.findall(r'"([^"]*iPhone[^"]*)"', seg)
    builds = sorted(set(v.split('_')[-1] for v in vals))
    print('  %-9s -> %d entries, devices=%d, builds=%s'
          % (vk, len(vals), len(set(vals)), builds))
