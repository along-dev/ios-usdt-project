import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import re

p = QIANKE_SRC + r'\qianke\qianke0301.sql'
s = open(p, encoding='utf-8', errors='replace').read()
lines = s.split('\n')
print('total lines:', len(lines), 'bytes:', len(s))

ins = [i for i, l in enumerate(lines) if re.match(r'\s*INSERT INTO', l, re.I)]
print('INSERT INTO line count:', len(ins))
print('first INSERT line:', ins[0] + 1 if ins else None)
print('last  INSERT line:', ins[-1] + 1 if ins else None)

# Distribution of INSERT forms
multi = sum(1 for i in ins if 'VALUES' in lines[i] and lines[i].rstrip().endswith(';'))
print('single-line complete INSERTs:', multi)
print('INSERT lines not ending with ;:', len(ins) - multi)

# Show DDL structure
print()
print('=== CREATE TABLE / other statement kinds ===')
kinds = {}
for l in lines:
    m = re.match(r'\s*(CREATE TABLE|CREATE INDEX|CREATE UNIQUE|ALTER TABLE|DROP TABLE|INSERT INTO|SET |LOCK TABLES|UNLOCK TABLES|/\*|--|\) ENGINE)', l, re.I)
    if m:
        k = m.group(1).upper().strip()
        kinds[k] = kinds.get(k, 0) + 1
for k, v in sorted(kinds.items(), key=lambda x: -x[1]):
    print('  %-16s %d' % (k, v))

print()
print('=== first 5 INSERT lines (truncated) ===')
for i in ins[:5]:
    print('  L%d: %s' % (i + 1, lines[i][:120]))

print()
print('=== sample: wallet INSERT containing mnemonic ===')
for i in ins:
    if 'phrase' in lines[i] and len(lines[i]) > 200:
        print('  L%d: %s' % (i + 1, lines[i][:400]))
        break
