import json, collections, re
d = json.load(open(r'E:\USDT项目\09-docs\reports\_d1c0_route_scan.json', encoding='utf-8'))
uniq = [tuple(x) for x in d['unique']]

def show(title, pred):
    sel = sorted([(m, p) for m, p in uniq if pred(m, p)])
    print('=== %s : %d ===' % (title, len(sel)))
    for m, p in sel:
        print('  %-6s %s' % (m, p))
    print()

show('api-prefixed routes (/api/...)', lambda m, p: p.startswith('/api/'))
show('NON-api routes (no /api prefix)', lambda m, p: not p.startswith('/api/'))
