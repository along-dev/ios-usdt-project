# -*- coding: utf-8 -*-
"""D4-C2 base：11-payment 下含凭据的文件清单（二进制模式测 eol/bytes，P-36）。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib
import os

ROOT = USDT_ROOT
D = os.path.join(ROOT, "11-payment")

NEEDLES = {
    "PASSWORD": b"HJAOxU46",
    "JWT": b"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
    "ACCESSKEY": b"BlVnlKWzllSGLm47BkWahzRq",
    "SECRETKEY": b"0r3W6Br2y8HK9VGzm5J9HXDwopY0J7SqeN6yzYqM",
}

rows = []
for dp, dn, fns in os.walk(D):
    dn[:] = [d for d in dn if d not in ("node_modules", ".git", "__pycache__")]
    for fn in fns:
        p = os.path.join(dp, fn)
        try:
            if os.path.getsize(p) > 20 * 1024 * 1024:
                continue
            raw = open(p, "rb").read()
        except Exception:
            continue
        tags = [k for k, v in NEEDLES.items() if v in raw]
        if not tags:
            continue
        crlf = raw.count(b"\r\n")
        lf = raw.count(b"\n") - crlf
        cr = raw.count(b"\r") - crlf
        eol = "MIXED" if (crlf and lf) else ("CRLF" if crlf else ("LF" if lf else "NONE"))
        rows.append({
            "rel": os.path.relpath(p, ROOT),
            "tags": tags,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "eol": eol,
        })

rows.sort(key=lambda r: r["rel"])
print("=== 11-payment 下含凭据的文件（%d 个）===" % len(rows))
for r in rows:
    print("  %-46s %-22s %s  %6d  %s" % (r["rel"][12:], ",".join(r["tags"]), r["sha256"][:16], r["bytes"], r["eol"]))

print("")
print("=== 汇总 ===")
from collections import Counter
c = Counter()
for r in rows:
    for t in r["tags"]:
        c[t] += 1
for k, v in c.items():
    print("  %-12s %d 个文件" % (k, v))
