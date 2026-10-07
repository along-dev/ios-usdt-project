import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, json

W = QIANKE_SRC + r'\qianke_web0304\web - 副本'
print('#' * 74)
print('# 潜客后台 Vue 结构:', W)
print('#' * 74)
if os.path.isdir(W):
    for f in sorted(os.listdir(W)):
        fp = os.path.join(W, f)
        if os.path.isfile(fp):
            print('   %-34s %10d' % (f, os.path.getsize(fp)))
        else:
            n = sum(len(fn) for _, _, fn in os.walk(fp))
            print('   %-34s <dir> %d files' % (f + os.sep, n))
    # package.json
    pj = os.path.join(W, 'package.json')
    if os.path.isfile(pj):
        d = json.load(open(pj, encoding='utf-8'))
        print()
        print('   name=%s version=%s' % (d.get('name'), d.get('version')))
        print('   dependencies:', list(d.get('dependencies', {}).keys()))
        print('   scripts:', list(d.get('scripts', {}).keys()))

# views / api 目录（判断有哪些功能页）
print()
for sub in [r'src\views', r'src\api', r'src\router']:
    d = os.path.join(W, sub)
    if os.path.isdir(d):
        print('=== %s ===' % sub)
        for dp, dn, fn in os.walk(d):
            depth = dp[len(d):].count(os.sep)
            if depth <= 1:
                print('  ', dp[len(W):])
                for f in sorted(fn)[:12]:
                    print('      ', f)
