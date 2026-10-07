import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import re

files = [
    (IOS_ROOT + r'\_buildtest\09-docs\analysis\整合复刻执行方案_主方案.md', [997, 998, 1013]),
    (IOS_ROOT + r'\_buildtest\09-docs\analysis\android-admin-recovery.md', [344]),
]
for fp, lns in files:
    print('=' * 70)
    print(fp)
    lines = open(fp, encoding='utf-8', errors='replace').read().split('\n')
    for ln in lns:
        print('  L%d: %s' % (ln, lines[ln - 1]))
