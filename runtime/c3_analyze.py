"""
C3 前置判定辅助：梳理 coruna 的版本表结构，判断 17.3+ 的扩展可行性与影响面。

关键问题：
  1. PSNMWj / LTgSl5 表的 minVersion 语义是"下界"（选择逻辑 if (GFx77t > iOSVersion) break）
  2. 追加 17.3+ 条目会改变既有版本命中的条目吗？
  3. 17.3-18.3 落在哪个区间？
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

P = IOS_ROOT + r'\ios15-17版本漏洞\ios15-17版本漏洞\coruna\platform_module.js'
s = open(P, encoding='utf-8', errors='replace').read()


def table(name):
    m = re.search(re.escape(name) + r'\s*[:=]\s*\[', s)
    i = s.index('[', m.start())
    depth = 0
    for j in range(i, len(s)):
        if s[j] == '[':
            depth += 1
        elif s[j] == ']':
            depth -= 1
            if depth == 0:
                return s[i:j + 1]
    return None


for name in ['PSNMWj', 'LTgSl5', 'RoAZdq']:
    t = table(name)
    vals = sorted((int(x) for x in re.findall(r'GFx77t:\s*(\d+)', t)), reverse=True)
    print('=== %s ===' % name)
    print('  条目数:', len(vals))
    print('  降序:', vals)
    print()

# 选择逻辑
print('=== 选择逻辑 ===')
for m in re.finditer(r'.{0,160}GFx77t\s*>\s*\w+.{0,100}', s):
    print('  ', m.group(0).strip()[:260])
    print()

# 目标区间 17.3 - 18.3 的数值表示
print('=== 目标区间数值 ===')
for v in ['17.3.0', '17.6.1', '18.0', '18.3.0', '18.3.2']:
    a, b, c = (v.split('.') + ['0', '0'])[:3]
    num = int(a) * 10000 + int(b) * 100 + int(c)
    print('  %-8s -> %d' % (v, num))

print()
print('=== PSNMWj 最低条目（承接所有更低版本）===')
t = table('PSNMWj')
last = t.rstrip().rstrip(']').rsplit('{', 2)[-2:]
for seg in last:
    print('  ', seg.strip()[:200])
