import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

PATS = {
    'JWT_SECRET': '586840011f5435723fdfb28b849b53c31dbb91a858c2137fa7fb9f7e7b904e03',
    'EXPORT_ENCRYPTION_KEY': 'HCRs35JHX7kuKHWh4ZBZBsPH3EiiBH4u',
    'DEFAULT_ADMIN_PASSWORD': 'DEFAULT_ADMIN_PASSWORD=admin',
}
# 只扫 _integration 下的文本产物（排除备份目录与工作目录）
root = IOS_ROOT + r'\_integration'
skip_dirs = ('_backup_', '_fix_work')
exts = ('.md', '.txt', '.json', '.ps1', '.py', '.js', '.yml', '.yaml')

hits = {k: [] for k in PATS}
for dp, dn, fn in os.walk(root):
    if any(s in dp for s in skip_dirs):
        continue
    for f in fn:
        if not f.lower().endswith(exts):
            continue
        fp = os.path.join(dp, f)
        try:
            if os.path.getsize(fp) > 5_000_000:
                continue
            s = open(fp, encoding='utf-8', errors='replace').read()
        except Exception:
            continue
        for name, pat in PATS.items():
            for m in re.finditer(re.escape(pat), s):
                ln = s[:m.start()].count('\n') + 1
                hits[name].append((fp, ln))

for name in PATS:
    print('=== %s : %d 处' % (name, len(hits[name])))
    for fp, ln in hits[name]:
        print('    %s:%d' % (fp, ln))
