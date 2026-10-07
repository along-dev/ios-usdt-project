import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

base = QIANKE_SRC + r'\qianke'
fp = os.path.join(base, 'blockchain', 'scan.go')
s = open(fp, encoding='utf-8', errors='replace').read()
print('scan.go lines:', s.count('\n') + 1)
print('=== function signatures ===')
for m in re.finditer(r'^func\s+(\([^)]*\)\s*)?(\w+)\s*\(', s, re.M):
    print('   ', m.group(0).strip())
print()
print('=== keyword counts ===')
for kw in ['collect', 'Collect', 'settle', 'Settle', 'packet', 'Packet',
           'SendTransaction', 'Transfer', 'privateKey', 'PrivateKey', 'toAddress']:
    c = s.count(kw)
    if c:
        print('   %-16s x%d' % (kw, c))
print()
print('=== excerpt around first Collect/settle mention ===')
for kw in ['Collect', 'collect']:
    i = s.find(kw)
    if i > 0:
        print(s[max(0, i - 300):i + 500])
        break

# packet.go model
print()
print('=== model/app/packet.go ===')
p2 = os.path.join(base, 'model', 'app', 'packet.go')
print(open(p2, encoding='utf-8', errors='replace').read()[:1200])
