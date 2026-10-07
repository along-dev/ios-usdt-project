"""P1-1 复核：rce_loader.js 阶段状态机行号归属。
方案引用的行号（1282/1508/1535/1554/1473/1475/1477/1379/1385）属于哪一份？
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os

A = IOS_ROOT + r'\ios15-17版本漏洞\ios15-17版本漏洞\darksword\rce_loader.js'   # 260 行
B = IOS_ROOT + r'\src_recon\mirror\alibaba\expires\rce_loader.js'              # 1721 行

def lineno(path, pat, limit=5):
    out = []
    for i, line in enumerate(open(path, encoding='utf-8', errors='ignore'), 1):
        if pat in line:
            out.append(i)
            if len(out) >= limit:
                break
    return out

ANCHORS = [
    'chainCkSetStage("boot")',
    'chainCkSetStage("rce")',
    'chainCkSetStage("warm")',
    'chainCkSetStage("sbx0")',
    'chainCkSetStage("pe_head")',
    'chainCkSetStage("pe_ready")',
    'chainCkSetStage("done")',
    'chainCkSetStage("sbx1")',      # ★ 方案称"零命中"
    'stage1_progress',
    'fcall_ready',
]

print('=' * 80)
print('P1-1 复核：阶段设置点行号')
print('=' * 80)
print(f'{"锚点":<34} {"darksword(260)":<18} {"src_recon(1721)":<18}')
print('-' * 80)
for a in ANCHORS:
    ha = lineno(A, a)
    hb = lineno(B, a)
    sa = ','.join(map(str, ha)) or '—'
    sb = ','.join(map(str, hb)) or '—'
    print(f'{a[:33]:<34} {sa:<18} {sb:<18}')

print()
print('=' * 80)
print('方案 §4.1.3 状态机引用的行号（归属判定）')
print('=' * 80)
CITED = [1282, 1508, 1535, 1554, 1473, 1475, 1477, 1379, 1385]
for ln in CITED:
    def at(path, n):
        with open(path, encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f, 1):
                if i == n:
                    return line.strip()[:78]
        return '(EOF)'
    print(f'\n  行 {ln}:')
    print(f'    darksword : {at(A, ln)}')
    print(f'    src_recon : {at(B, ln)}')

print()
print('=' * 80)
print('★ 关键核实：方案称 sbx1 在 loader 中「零命中」')
print('=' * 80)
for pat in ['chainCkSetStage("sbx1")', "'sbx1'", '"sbx1"']:
    ha = lineno(A, pat, 10)
    hb = lineno(B, pat, 10)
    print(f'  {pat:<28} darksword={len(ha)} 处  src_recon={len(hb)} 处  {hb[:6]}')
