import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

V = IOS_ROOT + r'\ios15-17版本漏洞\ios15-17版本漏洞\coruna'

# 1) group.html 里的版本选择逻辑（运行时如何决定用哪条链）
for fname in ['group.html', 'index.html']:
    fp = os.path.join(V, fname)
    if not os.path.isfile(fp):
        continue
    s = open(fp, encoding='utf-8', errors='replace').read()
    print('=' * 76)
    print(fname, 'size=', len(s))
    print('=' * 76)
    # 找版本判断/Stage 选择
    for pat in [r'.{0,90}iOSVersion.{0,90}', r'.{0,70}Stage1_.{0,70}',
                r'.{0,70}16\.6.{0,90}', r'.{0,80}17\.2.{0,80}']:
        hits = re.findall(pat, s)
        seen = set()
        for h in hits[:6]:
            h = h.strip()
            if h not in seen:
                seen.add(h)
                print('   ', h[:170])
        print('   ---')
    print()
