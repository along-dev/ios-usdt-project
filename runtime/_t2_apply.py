# -*- coding: utf-8 -*-
"""T2：更正 需求文档.md 的 chain-router 边界陈述（§3.1 验收 1.6 + §3.3 裁决）。

★ 二进制读写，零换行转换（P-36）。
"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib

P = USDT_ROOT + r"\09-docs\analysis\需求文档.md"

OLD_1 = ("| 1.6 | ~~iOS 两条链可被正确路由~~ **→ 已裁决降为二期（2026 本轮，见 §3.3）** | "
         "**不再作为一期验收项**。原验收说明保留作溯源：原型已验证（源侧）；产物未接入 —— "
         "`chain-router.js` 等 4 个文件**不在 `E:\\USDT项目` 内**；59")

NEW_1 = ("| 1.6 | ~~iOS 两条链可被正确路由~~ **→ 曾裁决降为二期（见 §3.3）** | "
         "**★ 实测更正（二期 T2，2026 本轮）**：产物**已接入** —— "
         "`app.js:18` `import { c2Plugin } from './plugins/c2/index.js'` + "
         "`app.js:70` `await fastify.register(c2Plugin)`；"
         "`chain-router.js` **在** `02-backend-node/src_restored/plugins/c2/services/`"
         "（**并非「不在 `E:\\USDT项目` 内」**），**203 行**，被 3 个模块 import；"
         "**C-3 判据 GREEN**（`verify_entries_coruna.mjs` 实测 entries **15/5** 通过）。"
         "★ 原「产物未接入」的陈述**已过期**，保留作溯源：")

raw = open(P, "rb").read()
before = hashlib.sha256(raw).hexdigest()
print("  base sha256: %s" % before)
print("  base bytes : %d" % len(raw))

n1 = raw.count(OLD_1.encode("utf-8"))
print("  OLD_1 命中: %d" % n1)
if n1 != 1:
    print("  ★ 命中数不为 1 ⇒ abort（可能已被 T1 改动影响）")
    raise SystemExit(1)

out = raw.replace(OLD_1.encode("utf-8"), NEW_1.encode("utf-8"))

crlf_b, crlf_a = raw.count(b"\r\n"), out.count(b"\r\n")
lf_b = raw.count(b"\n") - crlf_b
lf_a = out.count(b"\n") - crlf_a
print("  eol 保持: CRLF %d→%d, LONE_LF %d→%d" % (crlf_b, crlf_a, lf_b, lf_a))
assert crlf_b == crlf_a and lf_b == lf_a, "eol 变了！"

open(P, "wb").write(out)
after = hashlib.sha256(open(P, "rb").read()).hexdigest()
print("  after sha256: %s" % after)
print("  after bytes : %d  (delta %+d)" % (len(out), len(out) - len(raw)))
print("  ✅ 已更正")
