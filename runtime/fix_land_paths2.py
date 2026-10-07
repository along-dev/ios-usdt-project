import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import re
fp = IOS_ROOT + r'\_integration\_fix_work\land_patches.py'
s = open(fp, encoding='utf-8').read()
# 统一目录已改为模块根布局：去掉 internal\ 前缀
repl = [
    ("r'internal\\model\\app\\machine.go'",  "r'model\\app\\machine.go'"),
    ("r'internal\\model\\app\\wallet.go'",   "r'model\\app\\wallet.go'"),
    ("r'internal\\model\\common.go'",        "r'model\\common.go'"),
    ("r'internal\\router\\app\\public.go'",  "r'router\\app\\public.go'"),
    ("r'internal\\service\\system\\sys_qianke.go'", "r'service\\system\\sys_qianke.go'"),
    ("r'internal\\api\\v1\\app\\collect_result.go'", "r'api\\v1\\app\\collect_result.go'"),
    ("r'internal\\api\\v1\\app\\wallet_status.go'",  "r'api\\v1\\app\\wallet_status.go'"),
    ("r'internal\\service\\app\\collect_result.go'", "r'service\\app\\collect_result.go'"),
]
n = 0
for a, b in repl:
    if a in s:
        s = s.replace(a, b); n += 1
open(fp, 'w', encoding='utf-8', newline='').write(s)
print('回退 internal 前缀: %d 条' % n)
