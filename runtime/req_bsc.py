import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

d = IOS_ROOT + r'\_analysis\gasleak_server\app_dist'
for fname in ['app_dist_core_tatum_constants.js', 'app_dist_core_db_models_params.js']:
    fp = os.path.join(d, fname)
    if not os.path.isfile(fp):
        continue
    s = open(fp, encoding='utf-8', errors='replace').read()
    print('=' * 74)
    print(fname, 'size=', len(s))
    print('=' * 74)
    for m in re.finditer(r'.{0,120}[bB][sS][cC].{0,120}', s):
        print('  ...', m.group(0).strip()[:230])
    print()

# derived-address 的 chain enum 再确认
fp = os.path.join(d, 'app_dist_core_db_models_derived-address.js')
s = open(fp, encoding='utf-8', errors='replace').read()
m = re.search(r'chain:\s*\{[^}]*\}', s)
print('derived-address chain 定义:', m.group(0) if m else 'NOT FOUND')
