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

p = IOS_ROOT + r'\ios15-17版本漏洞\ios15-17版本漏洞\darksword\sbx0_main_18.4.js'
s = open(p, encoding='utf-8', errors='replace').read()

# Extract the object literal passed to each Object.assign
for m in re.finditer(r'sbx0_offsets\s*=\s*Object\.assign\(sbx0_offsets\s*,\s*\{', s):
    ln = s[:m.start()].count('\n') + 1
    i = s.index('{', m.end() - 1)
    depth = 0
    end = None
    for j in range(i, len(s)):
        if s[j] == '{':
            depth += 1
        elif s[j] == '}':
            depth -= 1
            if depth == 0:
                end = j
                break
    body = s[i:end + 1]
    keys = re.findall(r'"([^"]+)"\s*:\s*\{', body)
    builds = sorted(set(k.split('_')[-1] for k in keys))
    devs = sorted(set(k.split('_')[0] for k in keys))
    print('Object.assign at line %d: adds keys=%d devices=%d builds=%s'
          % (ln, len(keys), len(devs), builds))

# Now simulate the runtime merge: start with L28 literal, then apply both assigns
allkeys = []
# L28 literal
m0 = re.search(r'sbx0_offsets\s*=\s*\{', s)
i = s.index('{', m0.end() - 1)
depth = 0
for j in range(i, len(s)):
    if s[j] == '{':
        depth += 1
    elif s[j] == '}':
        depth -= 1
        if depth == 0:
            end = j
            break
allkeys += re.findall(r'"([^"]+)"\s*:\s*\{', s[i:end + 1])
for m in re.finditer(r'sbx0_offsets\s*=\s*Object\.assign\(sbx0_offsets\s*,\s*\{', s):
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
    allkeys += re.findall(r'"([^"]+)"\s*:\s*\{', s[i:end + 1])

u = sorted(set(allkeys))
from collections import Counter
c = Counter(k.split('_')[-1] for k in u)
print()
print('=== RUNTIME MERGED sbx0_offsets ===')
print('total key occurrences:', len(allkeys))
print('unique keys:', len(u))
print('unique devices:', len(set(k.split('_')[0] for k in u)))
print('builds:')
for b in sorted(c):
    print('   %s -> %d devices' % (b, c[b]))
