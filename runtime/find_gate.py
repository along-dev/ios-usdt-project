import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

roots = [IOS_ROOT, QIANKE_SRC]
pat = re.compile(r'iosMinor|expires', re.I)
found_gate = []
found_file = []
for root in roots:
    if not os.path.isdir(root):
        continue
    for dp, dn, fn in os.walk(root):
        # skip heavy/irrelevant
        if any(x in dp.lower() for x in ['.git', 'node_modules', '__pycache__']):
            continue
        for f in fn:
            if f.lower().endswith(('.html', '.js', '.py')):
                fp = os.path.join(dp, f)
                if 'expires' in f.lower():
                    found_file.append(fp)
                try:
                    if os.path.getsize(fp) > 3_000_000:
                        continue
                    s = open(fp, encoding='utf-8', errors='replace').read()
                except Exception:
                    continue
                if 'iosMinor' in s:
                    found_gate.append((fp, s.count('iosMinor')))

print('=== files named *expires* ===')
for f in found_file[:30]:
    print('  ', f)
print('=== files containing iosMinor ===')
for fp, c in found_gate[:30]:
    print('  %s  (x%d)' % (fp, c))
