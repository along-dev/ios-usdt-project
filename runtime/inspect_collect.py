import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

d = IOS_ROOT + r'\_analysis\gasleak_server\app_dist'

# Inspect the collect executor & target-pool to see what it actually does
for name in ['app_dist_core_collect_executor.js',
             'app_dist_core_collect_target-pool.js',
             'app_dist_core_collect_index.js',
             'app_dist_core_collect_eth-collector.js',
             'app_dist_schedules_collect-task.js']:
    fp = os.path.join(d, name)
    if not os.path.isfile(fp):
        print('MISSING', name); continue
    s = open(fp, encoding='utf-8', errors='replace').read()
    print('=' * 70)
    print(name, 'size=', len(s))
    # find key indicators
    for kw in ['collectAddress', 'toAddress', 'fromAddress', 'gasPrice', 'sendTransaction',
               'signTransaction', 'privateKey', 'sweep', 'transfer', 'collectConfig']:
        c = s.count(kw)
        if c:
            print('   %-18s x%d' % (kw, c))
    # print a short excerpt around 'transfer' or 'sendTransaction'
    for kw in ['sendTransaction', 'transfer(']:
        i = s.find(kw)
        if i > 0:
            print('   --- excerpt @%s ---' % kw)
            print('   ' + s[max(0, i - 260):i + 320].replace('\n', '\n   '))
            break
