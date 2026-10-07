# -*- coding: utf-8 -*-
"""检查 T26 的 3 个文件里 errors 的用法与 import。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os

files = [
    USDT_ROOT + r"\01-backend-go\main.go",
    USDT_ROOT + r"\01-backend-go\initialize\ensure_seed.go",
    USDT_ROOT + r"\01-backend-go\service\system\sys_initdb.go",
]

for p in files:
    if not os.path.isfile(p):
        print("  [缺失] %s" % p)
        continue
    s = io.open(p, encoding="utf-8", errors="replace").read()
    print("  %s:" % os.path.basename(p))
    print("    errors.Wrap : %d" % s.count("errors.Wrap"))
    print("    errors.New  : %d" % s.count("errors.New"))
    print("    errors.Is   : %d" % s.count("errors.Is"))
    print("    fmt.Errorf  : %d" % s.count("fmt.Errorf"))
    print("    pkg/errors  : %d" % s.count("pkg/errors"))
    # 找 import 行
    for i, l in enumerate(s.splitlines(), 1):
        t = l.strip()
        if '"errors"' in t or "pkg/errors" in t or '"fmt"' in t:
            print("    import@%d: %s" % (i, t[:100]))
    print("")
