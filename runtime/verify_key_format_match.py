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

# 1) Runtime sbx0_offsets keys
p1 = IOS_ROOT + r'\ios15-17版本漏洞\ios15-17版本漏洞\darksword\sbx0_main_18.4.js'
s1 = open(p1, encoding='utf-8', errors='replace').read()
sbx0 = set()
m0 = re.search(r'sbx0_offsets\s*=\s*\{', s1)
i = s1.index('{', m0.end() - 1)
depth = 0
for j in range(i, len(s1)):
    if s1[j] == '{':
        depth += 1
    elif s1[j] == '}':
        depth -= 1
        if depth == 0:
            end = j
            break
sbx0 |= set(re.findall(r'"([^"]+)"\s*:\s*\{', s1[i:end + 1]))
for m in re.finditer(r'sbx0_offsets\s*=\s*Object\.assign\(sbx0_offsets\s*,\s*\{', s1):
    i = s1.index('{', m.end() - 1)
    depth = 0
    for j in range(i, len(s1)):
        if s1[j] == '{':
            depth += 1
        elif s1[j] == '}':
            depth -= 1
            if depth == 0:
                end = j
                break
    sbx0 |= set(re.findall(r'"([^"]+)"\s*:\s*\{', s1[i:end + 1]))

# 2) linkedit_to_device return values
p2 = IOS_ROOT + r'\ios15-17版本漏洞\ios15-17版本漏洞\darksword\rce_module.js'
s2 = open(p2, encoding='utf-8', errors='replace').read()
m = re.search(r'const linkedit_to_device\s*=\s*\{', s2)
i = s2.index('{', m.end() - 1)
depth = 0
for j in range(i, len(s2)):
    if s2[j] == '{':
        depth += 1
    elif s2[j] == '}':
        depth -= 1
        if depth == 0:
            end = j
            break
body = s2[i:end + 1]
vals = set(re.findall(r'"([^"]*iPhone[^"]*)"', body))

print('runtime sbx0_offsets unique keys :', len(sbx0))
print('linkedit_to_device unique values:', len(vals))
print()
print('values in linkedit_to_device NOT in sbx0_offsets:')
missing = sorted(vals - sbx0)
for v in missing:
    print('   ', v)
print('   count:', len(missing))
print()
print('sbx0_offsets keys NOT produced by linkedit_to_device:')
extra = sorted(sbx0 - vals)
for v in extra:
    print('   ', v)
print('   count:', len(extra))
print()
print('EXACT MATCH:', vals == sbx0)
