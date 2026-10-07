"""P1-2 复核：两份 sbx1_main.js 的行号对应关系。
方案 §4.1.3 引用的行号（6089/6098/5520/5163）属于哪一份？
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

A = IOS_ROOT + r'\ios15-17版本漏洞\ios15-17版本漏洞\darksword\sbx1_main.js'   # 6862 行
B = IOS_ROOT + r'\src_recon\mirror\alibaba\expires\sbx1_main.js'              # 7812 行

# 方案中引用的锚点（§4.1.3 沙箱逃逸机制表）
ANCHORS = {
    'IOSurfacePrefetchPages': None,
    'scaler_transfer': None,
    'SandboxRegistrationForDestURL': None,
    'Remaker_TemporaryDirectoryURL': None,
    '0x77303074': None,
    'calloc() survived': None,
    'w00t': None,
}

def find(path, pat):
    hits = []
    for i, line in enumerate(open(path, encoding='utf-8', errors='ignore'), 1):
        if pat in line:
            hits.append(i)
    return hits

print('=' * 78)
print('P1-2 复核：锚点在两份文件中的行号')
print('=' * 78)
print(f'{"锚点":<34} {"darksword(6862)":<20} {"src_recon(7812)":<20} 差')
print('-' * 78)
for pat in ANCHORS:
    ha = find(A, pat)
    hb = find(B, pat)
    sa = ','.join(map(str, ha[:3])) or '—'
    sb = ','.join(map(str, hb[:3])) or '—'
    diff = ''
    if ha and hb:
        d = hb[0] - ha[0]
        diff = f'+{d}' if d >= 0 else str(d)
    print(f'{pat[:33]:<34} {sa:<20} {sb:<20} {diff}')

print()
print('=' * 78)
print('方案 §4.1.3 引用的行号归属判定')
print('=' * 78)
cited = [6089, 6098, 5520, 5531, 5163, 5792, 5842]
for ln in cited:
    import itertools
    def at(path, n):
        with open(path, encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f, 1):
                if i == n:
                    return line.strip()[:90]
        return '(EOF)'
    la = at(A, ln)
    lb = at(B, ln)
    print(f'\n  行 {ln}:')
    print(f'    darksword : {la}')
    print(f'    src_recon : {lb}')
