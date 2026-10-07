import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os

base = QIANKE_SRC + r'\qianke'

# 1) app JWT 中间件
for rel in [r'middleware\app_jwt.go']:
    fp = os.path.join(base, rel)
    if os.path.isfile(fp):
        print('=' * 78)
        print(rel)
        print('=' * 78)
        print(open(fp, encoding='utf-8', errors='replace').read()[:2500])

# 2) app service 的 Device/Wallet handler 模式
fp = os.path.join(base, r'service\app\public.go')
if os.path.isfile(fp):
    s = open(fp, encoding='utf-8', errors='replace').read()
    print('=' * 78)
    print('service/app/public.go  size=%d' % len(s))
    print('=' * 78)
    print(s[:3000])
