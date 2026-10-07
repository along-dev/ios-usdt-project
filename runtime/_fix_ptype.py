# -*- coding: utf-8 -*-
"""修正 30-casbin-seed.sql：`ptype` → `p_type`（实库列名）。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import hashlib

p = USDT_ROOT + r"\07-db\migration\30-casbin-seed.sql"
raw = open(p, "rb").read()
before = hashlib.sha256(raw).hexdigest()

OLD = b"`ptype`"
NEW = b"`p_type`"
n = raw.count(OLD)
print("  base sha256:", before[:16], " bytes:", len(raw))
print("  命中 `ptype`:", n)

if n == 0:
    print("  ★ 无命中（可能已改）")
else:
    out = raw.replace(OLD, NEW)
    # eol 保形
    cb, ca = raw.count(b"\r\n"), out.count(b"\r\n")
    lb = raw.count(b"\n") - cb
    la = out.count(b"\n") - ca
    assert cb == ca and lb == la, "eol 变了"
    open(p, "wb").write(out)
    after = hashlib.sha256(open(p, "rb").read()).hexdigest()
    print("  → after", after[:16], " delta:", len(out) - len(raw))
    print("  ✅ 已替换")

# 复查
s = io.open(p, encoding="utf-8", errors="replace").read()
print("")
print("  复查：p_type 出现", s.count("p_type"), "次")
print("        旧 ptype 残留", s.count("\x60ptype\x60"), "次")
