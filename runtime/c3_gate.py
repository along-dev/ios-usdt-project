import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

V = IOS_ROOT + r'\ios15-17版本漏洞\ios15-17版本漏洞\coruna'

# 1) group.html 的真实版本门禁（1001 = 拒绝码）
fp = os.path.join(V, 'group.html')
s = open(fp, encoding='utf-8', errors='replace').read()
print('=' * 76)
print('group.html 版本门禁附近（找 13E4 / 16E4 / 1001）')
print('=' * 76)
for m in re.finditer(r'13E4|16E4|1001|2E4|17E4|18E4', s):
    st = max(0, m.start() - 300)
    print(s[st: m.start() + 400])
    print('-' * 70)
    break

# 2) 是否 index.html 才是投放入口
for f in ['index.html', 'group.html']:
    p = os.path.join(V, f)
    t = open(p, encoding='utf-8', errors='replace').read()
    print('%s: 含 Stage1 引用=%s, 含 1001=%s, 含 DEVICE_VERSIONS=%s, 大小=%d'
          % (f, 'Stage1_' in t, '1001' in t, 'DEVICE_VERSIONS' in t, len(t)))

# 3) group.html 里的链选择函数全貌
print()
print('=' * 76)
print('group.html 版本判定函数')
print('=' * 76)
i = s.find('13E4')
# 向上找 function 定义
j = s.rfind('function', 0, i)
print(s[j: j + 1800])
