import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

PATS = {
    'JWT': '586840011f5435723fdfb28b849b53c31dbb91a858c2137fa7fb9f7e7b904e03',
    'EXPORT': 'HCRs35JHX7kuKHWh4ZBZBsPH3EiiBH4u',
    'PWDADMIN': 'DEFAULT_ADMIN_PASSWORD=admin',
}
# build_unified.ps1 L232: Copy-Flat -From "$SRC_IOS\_integration" -Filter '*.md' -> 09-docs/analysis
# build_unified.ps1 L237: Copy-One recon\最终报告.md -> 09-docs\analysis\android-admin-recovery.md
roots = [IOS_ROOT + r'\_integration', IOS_ROOT + r'\recon', QIANKE_SRC, IOS_ROOT + r'\ios-xy-main', IOS_ROOT + r'\_analysis']
skip = ('_backup_', '_fix_work', 'node_modules', '.git')

for root in roots:
    if not os.path.isdir(root):
        print('MISSING', root); continue
    found = []
    for dp, dn, fn in os.walk(root):
        if any(s in dp for s in skip):
            continue
        for f in fn:
            if not f.lower().endswith(('.md', '.txt')):
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
                    found.append((fp, ln, name))
    print('=== root: %s  -> %d hits' % (root, len(found)))
    for fp, ln, name in found:
        print('    %s:%d  [%s]' % (fp, ln, name))
