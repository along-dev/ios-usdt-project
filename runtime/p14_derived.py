import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

d = IOS_ROOT + r'\_analysis\gasleak_server\app_dist'
fp = os.path.join(d, 'app_dist_core_db_models_derived-address.js')
s = open(fp, encoding='utf-8', errors='replace').read()
print('=== derived-address.js 全文 ===')
print(s)
