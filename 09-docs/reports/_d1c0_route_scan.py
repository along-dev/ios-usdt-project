# D1-C0 read-only recon: enumerate Fastify registered routes under src_restored
# Key point: key by FULL RELATIVE PATH so that routes/auth.js and
# middleware/auth.js (same basename, different dirs) cannot mask each other.
# All output is ASCII to survive PowerShell redirection encoding.
import re, os, json, collections

ROOT = r'E:\USDT项目\02-backend-node\src_restored'
OUT = r'E:\USDT项目\09-docs\reports\_d1c0_route_scan.json'
PAT = re.compile(r"""fastify\s*\.\s*(get|post|put|delete|patch|all|head|options)\s*\(\s*['"]([^'"]+)['"]""", re.I)

rows = []           # (relpath, line, method, path)
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d != 'node_modules']
    for fn in filenames:
        if not fn.endswith('.js'):
            continue
        full = os.path.join(dirpath, fn)
        rel = os.path.relpath(full, ROOT).replace('\\', '/')
        try:
            fh = open(full, 'r', encoding='utf-8', errors='replace')
        except Exception:
            continue
        with fh:
            for i, line in enumerate(fh, 1):
                for m in PAT.finditer(line):
                    rows.append((rel, i, m.group(1).upper(), m.group(2)))

rows.sort(key=lambda r: (r[0], r[1]))

per_file = collections.OrderedDict()
for rel, ln, meth, path in rows:
    per_file.setdefault(rel, []).append([ln, meth, path])
total = sum(len(v) for v in per_file.values())
uniq = sorted(set((m, p) for _, _, m, p in rows))

report = {
    'root': ROOT,
    'total_matches': total,
    'files_with_matches': len(per_file),
    'unique_method_path': len(uniq),
    'per_file': per_file,
    'unique': [[m, p] for m, p in uniq],
}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=1)

# ---- ASCII console summary ----
print('TOTAL_MATCHES=%d' % total)
print('FILES_WITH_MATCHES=%d' % len(per_file))
print('UNIQUE_METHOD_PATH=%d' % len(uniq))
print('--- per file ---')
for rel, items in per_file.items():
    print('%s -> %d' % (rel, len(items)))
