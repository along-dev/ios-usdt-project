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
import hashlib

p = IOS_ROOT + r'\ios15-17版本漏洞\ios15-17版本漏洞\coruna\platform_module.js'
s = open(p, encoding='utf-8', errors='replace').read()
# ★ T110（G-10）：计数判据同句打印被测文件快照哈希，把「期望值」与「磁盘真值」分离。
snap = hashlib.sha256(s.encode('utf-8')).hexdigest()

def table(name):
    """Extract the array literal for a runtime table."""
    m = re.search(re.escape(name) + r'\s*[:=]\s*\[', s)
    if not m:
        return None
    i = s.index('[', m.start())
    depth = 0
    for j in range(i, len(s)):
        if s[j] == '[':
            depth += 1
        elif s[j] == ']':
            depth -= 1
            if depth == 0:
                return s[i:j + 1]
    return None

for name in ['PSNMWj', 'LTgSl5', 'RoAZdq']:
    t = table(name)
    if t is None:
        print(name, 'NOT FOUND')
        continue
    # count entries = number of GFx77t occurrences (each entry has exactly one)
    entries = re.findall(r'GFx77t:\s*(\d+)', t)
    iv = sorted(int(x) for x in entries)
    print('%-8s entries=%d  snapshot_sha256=%s  minVersion range: %d .. %d' % (name, len(iv), snap, min(iv), max(iv)))
    print('          distinct:', sorted(set(iv)))
