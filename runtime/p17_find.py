import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import json, os

V = IOS_ROOT + r'\ios15-17版本漏洞\ios15-17版本漏洞\coruna'
P = os.path.join(V, 'payloads')
data = json.load(open(os.path.join(P, 'manifest.json'), encoding='utf-8', errors='replace'))

def getsize(e):
    return e.get('size')

def gettype(e):
    return e.get('type', -1)

# 1) 统计 manifest 规模
total_entries = 0
types = {}
for v in data.values():
    for e in v:
        total_entries += 1
        t = gettype(e)
        types[t] = types.get(t, 0) + 1
print('模块数:', len(data))
print('entry 总数:', total_entries)
print('type 分布:', dict(sorted(types.items())))
print()

# 2) 找 entryN_* 文件实际在哪
print('=== 全盘搜索 entry*_type0x* 文件 ===')
found = {}
for dp, dn, fn in os.walk(V):
    for f in fn:
        if f.startswith('entry') and '_type0x' in f:
            found.setdefault(dp, []).append(f)
for d, fs in found.items():
    print('  %s  -> %d 个文件' % (d[len(V):], len(fs)))
    for f in sorted(fs)[:6]:
        print('        %-34s %d' % (f, os.path.getsize(os.path.join(d, f))))
print()
print('找到的目录数:', len(found))
