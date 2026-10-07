# -*- coding: utf-8 -*-
"""T17 修正：断言应为「CRLF 数与 LONE_CR 数不变」，而非「LONE_LF 不变」。

★ 理由：新增内容用 LF，LONE_LF 自然增加 —— 这不是 eol 被改，而是新增文本。
★ 只有 CRLF 数 / LONE_CR 数的变化才说明 eol 风格被改。
"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib

P1 = USDT_ROOT + r"\09-docs\analysis\需求文档.md"

ANCHOR = "## 8. 已知缺陷登记（须纳入排期）"
INSERT = """## 8. 已知缺陷登记（须纳入排期）

> ★★ **F4 定位收口（二期 T17，2026 本轮 Owner 裁决）**：
> `06-android` 与 `11-payment` **是【交付物】**，不是"侦察素材"。
> 依据：① `06-android` 是 **需求 §3.1 #1.7（Android 三段链）的验收载体**；
> ② `11-payment` 已有 `README.md` 声明性质（**项目外目标的侦察/验证产物，
> 所有结论"未证实"，不构成本项目自身的安全保证**）；
> ③ 两者 **均不在 `_manifest.sha256`**（本就非"产物指纹"范围）。
> ⇒ **两者各须有 README**（`06-android` 由 T13 补建）。"""


def eol_stats(b):
    crlf = b.count(b"\r\n")
    lone_lf = b.count(b"\n") - crlf
    lone_cr = b.count(b"\r") - crlf
    return crlf, lone_lf, lone_cr


raw = open(P1, "rb").read()
before = hashlib.sha256(raw).hexdigest()
n = raw.count(ANCHOR.encode("utf-8"))
print("  [T17] 命中: %d  (base %s)" % (n, before[:16]))
if n != 1:
    print("    ★ 命中不为 1 ⇒ 跳过")
    raise SystemExit(1)

out = raw.replace(ANCHOR.encode("utf-8"), INSERT.encode("utf-8"))

cb, lb, crb = eol_stats(raw)
ca, la, cra = eol_stats(out)
print("    eol: CRLF %d→%d   LONE_LF %d→%d   LONE_CR %d→%d" % (cb, ca, lb, la, crb, cra))

# ★ 正确断言：eol 风格不变 = CRLF 数与 LONE_CR 数不变
if cb == ca and crb == cra:
    open(P1, "wb").write(out)
    after = hashlib.sha256(open(P1, "rb").read()).hexdigest()
    print("    ✅ eol 风格未变（CRLF=%d, LONE_CR=%d 恒定）；新增 %d 行 LF" % (ca, cra, la - lb))
    print("    ✅ after %s  (delta %+d)" % (after[:16], len(out) - len(raw)))
else:
    print("    ★ eol 风格被改 ⇒ 跳过")
