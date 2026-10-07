import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

d = IOS_ROOT + r'\_analysis\gasleak_server\app_dist'
# walletType 的取值集合：从 collector services 与 raw-data 中找
for fname in os.listdir(d):
    if not fname.endswith('.js'):
        continue
    fp = os.path.join(d, fname)
    try:
        s = open(fp, encoding='utf-8', errors='replace').read()
    except Exception:
        continue
    if 'walletType' not in s:
        continue
    # 找 enum 定义
    for m in re.finditer(r'walletType[^;]{0,200}', s):
        t = m.group(0)
        if 'enum' in t or '=' in t:
            print('%-60s %s' % (fname.replace('app_dist_', ''), t.replace('\n', ' ')[:170]))
            break

print()
print('=== 搜 walletType 的枚举字面量 ===')
pat = re.compile(r"\[[^\]]*'(?:Trust|MetaMask|imToken|TokenPocket|OKX|Coinbase|Binance)[^']*'[^\]]*\]")
for fname in os.listdir(d):
    if not fname.endswith('.js'):
        continue
    fp = os.path.join(d, fname)
    try:
        s = open(fp, encoding='utf-8', errors='replace').read()
    except Exception:
        continue
    for m in pat.finditer(s):
        print('  %-55s %s' % (fname.replace('app_dist_', ''), m.group(0)[:150]))
