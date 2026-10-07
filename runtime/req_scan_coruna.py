import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

V = IOS_ROOT + r'\ios15-17版本漏洞\ios15-17版本漏洞'

print('#' * 76)
print('# coruna 目录')
print('#' * 76)
for dp, dn, fn in os.walk(os.path.join(V, 'coruna')):
    depth = dp[len(V):].count(os.sep)
    if depth > 2:
        continue
    rel = dp[len(V):] or '\\'
    print('  ' + rel)
    for f in sorted(fn)[:25]:
        print('      %-58s %8d' % (f, os.path.getsize(os.path.join(dp, f))))

print()
print('#' * 76)
print('# darksword 顶层')
print('#' * 76)
for f in sorted(os.listdir(os.path.join(V, 'darksword'))):
    fp = os.path.join(V, 'darksword', f)
    if os.path.isfile(fp):
        print('      %-58s %8d' % (f, os.path.getsize(fp)))
