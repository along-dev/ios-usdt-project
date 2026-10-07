import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, re

W = QIANKE_SRC + r'\qianke_web0304\web - 副本\src'
# 找菜单/路由定义
for cand in ['router\\index.js', 'view\\layout\\menu', 'config']:
    p = os.path.join(W, cand)
    if os.path.isdir(p):
        print('DIR', cand, os.listdir(p)[:20])
    elif os.path.isfile(p):
        print('FILE', cand, os.path.getsize(p))

# 全量 view 目录（功能页）
vd = os.path.join(W, 'view')
if os.path.isdir(vd):
    print()
    print('=== view 功能页（二级）===')
    for dp, dn, fn in os.walk(vd):
        depth = dp[len(vd):].count(os.sep)
        if depth <= 1:
            rel = dp[len(vd):] or '\\'
            print('  %-40s dirs=%d files=%d' % (rel, len(dn), len(fn)))
            for f in sorted(fn)[:8]:
                print('        ', f)

# 找业务相关关键词
print()
print('=== 业务关键词命中（src 下）===')
kws = ['wallet', 'machine', 'agent', 'packet', 'bill', 'settlement', 'qianke',
       'device', 'collect', 'domain', 'channel']
hit = {}
for dp, dn, fn in os.walk(W):
    if 'node_modules' in dp:
        continue
    for f in fn:
        if not f.endswith(('.js', '.vue')):
            continue
        fp = os.path.join(dp, f)
        try:
            s = open(fp, encoding='utf-8', errors='replace').read()
        except Exception:
            continue
        for k in kws:
            if re.search(k, s, re.I):
                hit[k] = hit.get(k, 0) + 1
for k, v in sorted(hit.items(), key=lambda x: -x[1]):
    print('   %-14s %d 文件' % (k, v))
