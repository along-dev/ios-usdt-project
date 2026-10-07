# -*- coding: utf-8 -*-
"""R4-C4 重扫：privesc_results.json 全 30 条的凭据（正则已修正）。

★ 上一版正则的错误：`resp` 是【被转义的 JSON 字符串】，
  实际字符是 `\"AccessKey\": \"...\"`（**反斜杠 + 引号**），
  而我把 `\"` 当成转义引号（即纯 `"`）⇒ 必然失配 ⇒ 0 命中（假阴性）。
  ⇒ 修正为匹配**字面的反斜杠+引号**。
"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import json
import re

P = USDT_ROOT + r"\11-payment\privesc_results.json"
raw = io.open(P, encoding="utf-8", errors="replace").read()
d = json.loads(raw)

# 在 raw 中，resp 的值形如: "resp": "{\"Data\": {\"AccessKey\": \"xxx\", ..."
# 所以 raw 里的字面序列是：  \"AccessKey\": \"xxx\"
BS = "\\"          # 一个反斜杠
Q = '"'
# 匹配  \"Key\": \"VALUE\"
def pat_for(key):
    return re.compile(re.escape(BS + Q + key + BS + Q) + r"\s*:\s*" +
                      re.escape(BS + Q) + r"([^" + re.escape(BS) + Q + r"]+)")

PATS = [
    ("AccessKey", pat_for("AccessKey")),
    ("SecretKey", pat_for("SecretKey")),
    ("password", pat_for("password")),
    ("Password", pat_for("Password")),
    ("token", pat_for("token")),
    ("Token", pat_for("Token")),
    ("Bearer", re.compile(r"Bearer\s+([A-Za-z0-9_\-\.]{20,})")),
    ("JWT", re.compile(r"(eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,})")),
]

print("=== raw 扫描（修正后）===")
for name, pat in PATS:
    ms = pat.findall(raw)
    if ms:
        print("  %-12s %d 处" % (name, len(ms)))
        for x in ms[:3]:
            print("      %s" % str(x)[:80])
    else:
        print("  %-12s 0 处" % name)

print("")
print("=== 逐条（30 条）===")
hits_any = False
for i, r in enumerate(d):
    blob = json.dumps(r, ensure_ascii=False)
    flags = [name for name, pat in PATS if pat.search(blob)]
    if flags:
        hits_any = True
        print("  [%2d] tag=%-22s path=%-34s ★ %s"
              % (i, str(r.get("tag"))[:22], str(r.get("path"))[:34], ",".join(flags)))
if not hits_any:
    print("  （无）")

print("")
print("=== 结构（保形断言参考）===")
print("  条数:", len(d))
keys = set()
for r in d:
    if isinstance(r, dict):
        keys |= set(r.keys())
print("  键集合:", sorted(keys))
print("  CRLF:", raw.count("\r\n"), " LF:", raw.count("\n"))
print("  bytes:", len(raw.encode("utf-8")))
