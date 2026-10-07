# -*- coding: utf-8 -*-
"""T25-C6：脱敏 11-payment 内 2 个 .py 的明文 AccessKey。

★ 二进制读写，零换行转换（P-36）。
★ eol 断言：CRLF 数 + LONE_CR 数不变（P-37）。
★ 幂等：已替换过的跳过。
"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib
import os

ROOT = USDT_ROOT
KEY = "<REDACTED_ACCESSKEY>"
REPL = "<REDACTED_ACCESSKEY>"

TARGETS = [
    os.path.join(ROOT, "11-payment", "pw_privesc.py"),
    os.path.join(ROOT, "11-payment", "pw_privesc2.py"),
]


def eol(b):
    crlf = b.count(b"\r\n")
    return crlf, b.count(b"\n") - crlf, b.count(b"\r") - crlf


for p in TARGETS:
    if not os.path.isfile(p):
        print("  [缺失] %s" % p)
        continue
    raw = open(p, "rb").read()
    before = hashlib.sha256(raw).hexdigest()
    n = raw.count(KEY.encode("utf-8"))
    print("  %s" % os.path.basename(p))
    print("    base sha256: %s  bytes %d" % (before[:16], len(raw)))
    print("    明文命中: %d" % n)
    if n == 0:
        print("    ★ 已脱敏（幂等跳过）")
        continue
    out = raw.replace(KEY.encode("utf-8"), REPL.encode("utf-8"))
    cb, lb, crb = eol(raw)
    ca, la, cra = eol(out)
    print("    eol: CRLF %d→%d  LONE_LF %d→%d  LONE_CR %d→%d" % (cb, ca, lb, la, crb, cra))
    assert cb == ca and crb == cra, "eol 风格被改！"
    open(p, "wb").write(out)
    after = hashlib.sha256(open(p, "rb").read()).hexdigest()
    print("    → after %s  (delta %+d)" % (after[:16], len(out) - len(raw)))
    print("    ✅ 已脱敏")

print("")
print("=== 复查：产物树内残留 ===")
left = 0
for dp, dn, fns in os.walk(ROOT):
    dn[:] = [d for d in dn if d not in (".git", "node_modules", "__pycache__")]
    for f in fns:
        if not f.endswith((".py", ".js", ".json", ".txt")):
            continue
        fp = os.path.join(dp, f)
        try:
            b = open(fp, "rb").read()
        except Exception:
            continue
        if KEY.encode() in b:
            left += 1
            print("  ★ 残留: %s" % os.path.relpath(fp, ROOT))
print("  残留文件数: %d" % left)
