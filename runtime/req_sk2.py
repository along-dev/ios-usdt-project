import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

fp = QIANKE_SRC + r'\qianke\blockchain\scan.go'
s = open(fp, encoding='utf-8', errors='replace').read()
m = re.search(r'^func\s+Sk\s*\(', s, re.M)
rest = s[m.start():]
nxt = re.search(r'\nfunc\s', rest[1:])
seg = rest[:nxt.start() + 1] if nxt else rest

print('Sk 总行数:', seg.count('\n') + 1)
print()
# 找转账/签名相关段落
for kw in ['Transfer', 'SendTransaction', 'privateKey', 'PrivateKey', 'SignTransaction',
           'SkSend', 'ethClient', 'trx', 'RawTransaction']:
    idxs = [mm.start() for mm in re.finditer(re.escape(kw), seg)]
    if idxs:
        print('%-18s x%d' % (kw, len(idxs)))

print()
print('=== Transfer / 签名 段落（后半）===')
i = seg.find('Transfer')
if i < 0:
    i = seg.find('privateKey')
print(seg[max(0, i - 1500): i + 2500])
