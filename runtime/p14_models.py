import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

base = QIANKE_SRC + r'\qianke'

# 1) Go 模型 struct 字段（model/app/*.go）
print('#' * 78)
print('# 1) Go 模型实际字段')
print('#' * 78)
for name in ['machine.go', 'wallet.go', 'bill.go']:
    fp = os.path.join(base, 'model', 'app', name)
    if not os.path.isfile(fp):
        print('MISSING', name); continue
    s = open(fp, encoding='utf-8', errors='replace').read()
    print('\n=== %s ===' % name)
    for line in s.split('\n'):
        line = line.rstrip()
        if re.search(r'json:"|gorm:"column:', line):
            print('   ', line.strip())
