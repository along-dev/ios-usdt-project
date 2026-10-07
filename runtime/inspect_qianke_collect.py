import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

# 潜客侧归集相关：packet 表 / bill 表 / settlement，以及 model 定义
base = QIANKE_SRC + r'\qianke'
print('qianke dir exists:', os.path.isdir(base))

# 1) model 文件
md = os.path.join(base, 'model', 'app')
if os.path.isdir(md):
    print('=== model/app files ===')
    for f in sorted(os.listdir(md)):
        print('   ', f)

# 2) 搜 collect / 归集 / settlement 关键词
print()
print('=== grep collect|settle|packet in qianke (go/py/js) ===')
pat = re.compile(r'collect|settle|packet|gather', re.I)
hits = {}
for dp, dn, fn in os.walk(base):
    if any(x in dp for x in ['node_modules', '.git']):
        continue
    for f in fn:
        if not f.endswith(('.go', '.sql', '.yaml', '.yml')):
            continue
        fp = os.path.join(dp, f)
        try:
            s = open(fp, encoding='utf-8', errors='replace').read()
        except Exception:
            continue
        n = len(pat.findall(s))
        if n:
            hits[fp] = n
for fp, n in sorted(hits.items(), key=lambda x: -x[1])[:20]:
    print('   %4d  %s' % (n, fp[len(base):]))
