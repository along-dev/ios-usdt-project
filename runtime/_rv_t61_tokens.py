# -*- coding: utf-8 -*-
"""T61 重锚 · 独立复现「token 级例外核」：.ts 与 .js 的 null / tatumClient 计数差，
   并要求【本件】与【先例对】同形（记录件称 'null 少 2 / tatumClient 多 2'）。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io, re

PAIRS = [
    ("先例 balance-init", r"E:\IOS源码1\server\src\schedules\balance-init.ts",
     USDT_ROOT + r"\02-backend-node\src_restored\schedules\balance-init.js"),
    ("本件 balance-refresh", r"E:\IOS源码1\server\src\schedules\balance-refresh.ts",
     USDT_ROOT + r"\02-backend-node\src_restored\schedules\balance-refresh.js"),
]


def cnt(path):
    t = io.open(path, encoding="utf-8").read()
    return (len(re.findall(r"\bnull\b", t)), len(re.findall(r"\btatumClient\b", t)))


for label, ts, js in PAIRS:
    a, b = cnt(ts), cnt(js)
    print("%-22s .ts: null=%d tatumClient=%d   .js: null=%d tatumClient=%d   Δ null=%+d  Δ tatumClient=%+d"
          % (label, a[0], a[1], b[0], b[1], b[0] - a[0], b[1] - a[1]))

print()
print("== 逐处：基准传 null 的调用点 vs 新件 ==")
for label, ts, js in PAIRS:
    print("-- %s" % label)
    for name, p in ((".ts", ts), (".js", js)):
        for i, ln in enumerate(io.open(p, encoding="utf-8").read().splitlines(), 1):
            if re.search(r"getEthAddressBalances\(|getTronAddressBalances\(|getBtcAddressBalance\(", ln):
                print("   %s:%-4d %s" % (name, i, ln.strip()))
