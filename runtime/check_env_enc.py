import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

# .env encoding check
p = IOS_ROOT + r'\ios-xy-main\gasleak-system\.env'
b = open(p, 'rb').read()
print('=== .env bytes:', len(b))
print('first 3 bytes (BOM?):', b[:3].hex())
for enc in ['utf-8', 'gbk', 'utf-8-sig']:
    try:
        s = b.decode(enc)
        ok = True
    except Exception as e:
        ok = False
        s = ''
    print('decode %-10s -> %s' % (enc, 'OK' if ok else 'FAIL'))
    if ok:
        # show JWT line
        for l in s.splitlines():
            if 'JWT_SECRET' in l or 'DEFAULT_ADMIN' in l or 'EXPORT_ENCRYPTION' in l:
                print('    ', l)
        break

# sensitive key inventory in .env
print()
print('=== keys in .env ===')
txt = b.decode('utf-8', errors='replace')
for l in txt.splitlines():
    if '=' in l and not l.strip().startswith('#'):
        k = l.split('=', 1)[0]
        print('  ', k)
