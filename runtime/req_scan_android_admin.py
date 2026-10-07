import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os

# 1) Android 三段链
R = IOS_ROOT + r'\recon\apk'
print('#' * 74)
print('# Android 资产:', R)
print('#' * 74)
if os.path.isdir(R):
    for f in sorted(os.listdir(R)):
        fp = os.path.join(R, f)
        if os.path.isfile(fp):
            print('   %-40s %10d' % (f, os.path.getsize(fp)))
        else:
            n = sum(len(fn) for _, _, fn in os.walk(fp))
            print('   %-40s <dir> %d files' % (f + os.sep, n))

# 2) 潜客后台 Vue
print()
print('#' * 74)
print('# 潜客后台 Vue')
print('#' * 74)
for cand in [QIANKE_SRC + r'\qianke_web0304', QIANKE_SRC]:
    if os.path.isdir(cand):
        for d in sorted(os.listdir(cand))[:25]:
            print('   ', d)

print()
print('# 潜客顶层')
for d in sorted(os.listdir(QIANKE_SRC)):
    print('   ', d)
