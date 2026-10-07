import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os

base = QIANKE_SRC + r'\qianke'

# api/v1/app 下的 handler 文件
d = os.path.join(base, 'api', 'v1', 'app')
print('=== api/v1/app 目录 ===')
if os.path.isdir(d):
    for f in sorted(os.listdir(d)):
        print('   ', f, os.path.getsize(os.path.join(d, f)))
else:
    print('不存在:', d)

# 找 Device handler 实现
for dp, dn, fn in os.walk(os.path.join(base, 'api')):
    for f in fn:
        if f.endswith('.go'):
            fp = os.path.join(dp, f)
            s = open(fp, encoding='utf-8', errors='replace').read()
            if 'func (a *PublicApi) Device' in s or 'func (p *PublicApi) Device' in s:
                print()
                print('=== 找到 Device handler:', fp)
                print(s[:3000])

# response 包
for dp, dn, fn in os.walk(os.path.join(base, 'api')):
    if 'response' in dp and 'app' in dp:
        for f in fn:
            print('response file:', os.path.join(dp, f))
