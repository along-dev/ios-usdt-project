# -*- coding: utf-8 -*-
"""T17 + T3-2 修正版：保持 eol，且不改变行数结构。

★ 关键：F4_NOTE 必须【以原锚点结尾、且保持同样的换行结构】。
"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib

ROOT = USDT_ROOT
P1 = ROOT + r"\09-docs\analysis\需求文档.md"
P2 = ROOT + r"\09-docs\analysis\问题登记册.md"

# ---------- T17：在 §8 标题【后】插入说明（保留原锚点本体）----------
ANCHOR = "## 8. 已知缺陷登记（须纳入排期）"
INSERT = """## 8. 已知缺陷登记（须纳入排期）

> ★★ **F4 定位收口（二期 T17，2026 本轮 Owner 裁决）**：
> `06-android` 与 `11-payment` **是【交付物】**，不是"侦察素材"。
> 依据：① `06-android` 是 **需求 §3.1 #1.7（Android 三段链）的验收载体**；
> ② `11-payment` 已有 `README.md` 声明性质（**项目外目标的侦察/验证产物，
> 所有结论"未证实"，不构成本项目自身的安全保证**）；
> ③ 两者 **均不在 `_manifest.sha256`**（本就非"产物指纹"范围）。
> ⇒ **两者各须有 README**（`06-android` 由 T13 补建）。"""

raw = open(P1, "rb").read()
before = hashlib.sha256(raw).hexdigest()
n = raw.count(ANCHOR.encode("utf-8"))
print("  [T17] 命中: %d  (base %s)" % (n, before[:16]))
if n == 1:
    out = raw.replace(ANCHOR.encode("utf-8"), INSERT.encode("utf-8"))
    crlf_b, crlf_a = raw.count(b"\r\n"), out.count(b"\r\n")
    lf_b = raw.count(b"\n") - crlf_b
    lf_a = out.count(b"\n") - crlf_a
    print("    eol: CRLF %d→%d  LONE_LF %d→%d" % (crlf_b, crlf_a, lf_b, lf_a))
    if crlf_b == crlf_a and lf_b == lf_a:
        open(P1, "wb").write(out)
        after = hashlib.sha256(open(P1, "rb").read()).hexdigest()
        print("    ✅ after %s  (delta %+d)" % (after[:16], len(out) - len(raw)))
    else:
        print("    ★ eol 不一致 ⇒ 跳过（不写入）")
else:
    print("    ★ 命中不为 1 ⇒ 跳过")

# ---------- T3-2：问题登记册 N-2 ----------
OLD_N2 = "| 6 | `signing-key`（N-2） | **按真值脱敏** | `待编码` |"
NEW_N2 = ("| 6 | `signing-key`（N-2） | ~~按真值脱敏~~ **实为占位符** | "
          "**✅ 已确认（非真值）**——实测 `config.yaml.example:9/97` = `${SIGNING_KEY}`，**无需脱敏**（二期 T3） |")

raw2 = open(P2, "rb").read()
before2 = hashlib.sha256(raw2).hexdigest()
n2 = raw2.count(OLD_N2.encode("utf-8"))
print("  [T3-2] 命中: %d  (base %s)" % (n2, before2[:16]))
if n2 == 1:
    out2 = raw2.replace(OLD_N2.encode("utf-8"), NEW_N2.encode("utf-8"))
    crlf_b, crlf_a = raw2.count(b"\r\n"), out2.count(b"\r\n")
    lf_b = raw2.count(b"\n") - crlf_b
    lf_a = out2.count(b"\n") - crlf_a
    print("    eol: CRLF %d→%d  LONE_LF %d→%d" % (crlf_b, crlf_a, lf_b, lf_a))
    if crlf_b == crlf_a and lf_b == lf_a:
        open(P2, "wb").write(out2)
        after2 = hashlib.sha256(open(P2, "rb").read()).hexdigest()
        print("    ✅ after %s  (delta %+d)" % (after2[:16], len(out2) - len(raw2)))
    else:
        print("    ★ eol 不一致 ⇒ 跳过")
else:
    print("    ★ 命中不为 1 ⇒ 跳过")
