import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

# 1) gasleak 侧其余模型字段
d = IOS_ROOT + r'\_analysis\gasleak_server\app_dist'
for fname in ['app_dist_core_db_models_device.js',
              'app_dist_core_db_models_wallet-data.js',
              'app_dist_core_db_models_mnemonic.js',
              'app_dist_core_db_models_channel.js']:
    fp = os.path.join(d, fname)
    if not os.path.isfile(fp):
        print('MISSING', fname); continue
    s = open(fp, encoding='utf-8', errors='replace').read()
    keys = re.findall(r'^\s{2,6}([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*\{', s, re.M)
    print('=== %s' % fname)
    print('    keys:', sorted(set(keys)))
    # uniqueId / productType 是否存在
    for kw in ['uniqueId', 'productType', 'channelCode', 'iosVersion', 'firstSeen', 'walletType', 'code']:
        if kw in s:
            i = s.find(kw)
            print('    [%s] %s' % (kw, s[max(0,i-40):i+90].replace('\n',' ')[:130]))
    print()

# 2) 潜客 wallet.type 的实际取值（从 INSERT 数据看，但已被脱敏；改看 SQL 注释/代码）
sql = QIANKE_SRC + r'\qianke\qianke0301.sql'
s = open(sql, encoding='utf-8', errors='replace').read()
m = re.search(r'CREATE TABLE\s+`wallet`.*?COMMENT', s, re.S | re.I)
print('=== wallet 建表注释 ===')
i = s.find('CREATE TABLE `wallet`')
print(s[i:i+400])
