import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import json, os

P = IOS_ROOT + r'\ios15-17版本漏洞\ios15-17版本漏洞\coruna\payloads'
M = os.path.join(P, 'manifest.json')
data = json.load(open(M, encoding='utf-8', errors='replace'))

print('顶层键数:', len(data))
k0 = list(data)[0]
print('首个键:', k0)
print()
print('首个值的结构:')
print(json.dumps(data[k0], ensure_ascii=False, indent=2)[:2200])
print()
print('=== payloads 目录实际文件 ===')
for f in sorted(os.listdir(P)):
    fp = os.path.join(P, f)
    if os.path.isfile(fp):
        print('   %-46s %10d' % (f, os.path.getsize(fp)))
