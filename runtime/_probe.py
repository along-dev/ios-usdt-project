import re
src = open(USDT_ROOT + r"\01-backend-go\blockchain\scan.go", encoding="utf-8").read()
src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
src = "\n".join(l.split("//")[0] for l in src.splitlines())
pat = r"time\.AfterFunc\s*\([^)]*,\s*func\s*\(\s*\)\s*\{"
print("regex matches:", [m.start() for m in re.finditer(pat, src)])
for m in re.finditer(r"time\.AfterFunc", src):
    print("--- at", m.start(), "---")
    print(repr(src[m.start():m.start()+160]))

import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))