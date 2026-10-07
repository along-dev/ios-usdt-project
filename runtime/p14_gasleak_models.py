import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

d = IOS_ROOT + r'\_analysis\gasleak_server\app_dist'

def show(fname, kws):
    fp = os.path.join(d, fname)
    if not os.path.isfile(fp):
        print('MISSING', fname); return
    s = open(fp, encoding='utf-8', errors='replace').read()
    print('=' * 74)
    print(fname, 'size=', len(s))
    # extract schema field definitions
    for m in re.finditer(r'(\w+)\s*:\s*\{\s*type\s*:\s*([A-Za-z\[\]"\']+)', s):
        pass
    # mongoose-ish schema object keys
    keys = re.findall(r'^\s{2,6}([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*\{', s, re.M)
    if keys:
        print('   schema keys:', sorted(set(keys))[:40])
    for kw in kws:
        c = s.count(kw)
        if c:
            print('   %-16s x%d' % (kw, c))

show('app_dist_core_db_models_collect-log.js',
     ['txHash', 'amount', 'chain', 'toAddress', 'walletId', 'uniqueId'])
show('app_dist_core_db_models_collect-target.js',
     ['address', 'chain', 'channelCode'])
show('app_dist_core_db_models_derived-address.js',
     ['address', 'privateKey', 'chain'])
show('app_dist_core_db_models_collect-config.js',
     ['threshold', 'chain', 'token', 'channelCode'])
