# Compare route counts between src and src_restored, keyed by FULL RELATIVE PATH.
import re, os, collections

PAT = re.compile(r"""fastify\s*\.\s*(get|post|put|delete|patch|all|head|options)\s*\(\s*['"]([^'"]+)['"]""", re.I)

def scan(ROOT):
    per = collections.OrderedDict()
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d != 'node_modules']
        for f in fn:
            if not f.endswith('.js'):
                continue
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, ROOT).replace('\\', '/')
            try:
                t = open(p, encoding='utf-8', errors='replace').read()
            except Exception:
                continue
            hits = PAT.findall(t)
            if hits:
                per[rel] = len(hits)
    return per

for ROOT, label in [(r'E:\USDT项目\02-backend-node\src', 'src'),
                    (r'E:\USDT项目\02-backend-node\src_restored', 'src_restored')]:
    per = scan(ROOT)
    print('=== %s ===' % label)
    print('files=%d  routes=%d' % (len(per), sum(per.values())))
    for k, v in per.items():
        print('   %-52s %d' % (k, v))
    print()
