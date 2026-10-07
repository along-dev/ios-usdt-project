import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os

base = QIANKE_SRC + r'\qianke'
print('#' * 74)
print('# 潜客 Go 后端结构')
print('#' * 74)
for sub in ['api', 'router', 'service', 'model', 'middleware', 'initialize', 'core', 'config']:
    d = os.path.join(base, sub)
    if not os.path.isdir(d):
        print('  MISSING', sub); continue
    print('\n=== %s/' % sub)
    for dp, dn, fn in os.walk(d):
        depth = dp[len(d):].count(os.sep)
        if depth > 1:
            continue
        rel = dp[len(d):] or '\\'
        js = [f for f in fn if f.endswith('.go')]
        if js or dn:
            print('   %-30s %s' % (rel, ', '.join(sorted(js)[:8])))
