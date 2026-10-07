# -*- coding: utf-8 -*-
"""T3：更正 需求文档.md 的 P1-3（已修）+ 问题登记册.md 的 N-2 待编码残留。
   T17：需求文档.md 的 F4 定位收口。

★ 二进制读写，零换行转换（P-36）。
"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib

ROOT = USDT_ROOT

# ---------- T3-1: 需求文档 P1-3 ----------
P1 = ROOT + r"\09-docs\analysis\需求文档.md"
OLD_13 = "| P1-3 | §6.2 \"gasleak 36 集合\" 张冠李戴（实为 v21998 的 36，gasleak 32） | 数据模型认知错 | 二期 |"
NEW_13 = ("| P1-3 | ~~§6.2 \"gasleak 36 集合\" 张冠李戴~~（实为 **v21998 的 36**，gasleak **32 model**） | "
          "数据模型认知错 | **✅ 已修（二期 T3）** |")

# ---------- T17: 需求文档 F4 定位收口（在 §8 表尾追加说明）----------
# 用 §8 表头作为锚点，在其后插入定性说明
ANCHOR = "## 8. 已知缺陷登记（须纳入排期）"
F4_NOTE = """## 8. 已知缺陷登记（须纳入排期）

> ★★ **F4 定位收口（二期 T17，2026 本轮 Owner 裁决）**：
> `06-android` 与 `11-payment` **是【交付物】**，不是"侦察素材"。
> 依据：① `06-android` 是**需求 §3.1 #1.7（Android 三段链）的验收载体**；
> ② `11-payment` 已有 `README.md` 声明性质（**项目外目标的侦察/验证产物，
> 所有结论"未证实"，不构成本项目自身的安全保证**）；
> ③ 两者**均不在 `_manifest.sha256`**（本就非"产物指纹"范围）。
> ⇒ **两者各须有 README**（`06-android` 由 T13 补建）。"""

for path, old, new, label in [
    (P1, OLD_13, NEW_13, "T3-1 需求文档 P1-3"),
    (P1, ANCHOR, F4_NOTE, "T17 需求文档 F4 收口"),
]:
    raw = open(path, "rb").read()
    before = hashlib.sha256(raw).hexdigest()
    n = raw.count(old.encode("utf-8"))
    print("  [%s] 命中: %d  (base %s)" % (label, n, before[:16]))
    if n != 1:
        print("    ★ 命中数不为 1 ⇒ 跳过")
        continue
    out = raw.replace(old.encode("utf-8"), new.encode("utf-8"))
    crlf_b, crlf_a = raw.count(b"\r\n"), out.count(b"\r\n")
    lf_b = raw.count(b"\n") - crlf_b
    lf_a = out.count(b"\n") - crlf_a
    assert crlf_b == crlf_a and lf_b == lf_a, "eol 变了！"
    open(path, "wb").write(out)
    after = hashlib.sha256(open(path, "rb").read()).hexdigest()
    print("    → after %s  (delta %+d)  eol OK" % (after[:16], len(out) - len(raw)))

# ---------- T3-2: 问题登记册 N-2 待编码 → 已确认 ----------
P2 = ROOT + r"\09-docs\analysis\问题登记册.md"
OLD_N2 = "| 6 | `signing-key`（N-2） | **按真值脱敏** | `待编码` |"
NEW_N2 = ("| 6 | `signing-key`（N-2） | ~~按真值脱敏~~ **实为占位符** | "
          "**✅ 已确认（非真值）**——实测 `config.yaml.example:9/97` = `${SIGNING_KEY}`，"
          "**无需脱敏**（二期 T3） |")

raw = open(P2, "rb").read()
before = hashlib.sha256(raw).hexdigest()
n = raw.count(OLD_N2.encode("utf-8"))
print("  [T3-2 登记册 N-2] 命中: %d  (base %s)" % (n, before[:16]))
if n == 1:
    out = raw.replace(OLD_N2.encode("utf-8"), NEW_N2.encode("utf-8"))
    crlf_b, crlf_a = raw.count(b"\r\n"), out.count(b"\r\n")
    lf_b = raw.count(b"\n") - crlf_b
    lf_a = out.count(b"\n") - crlf_a
    assert crlf_b == crlf_a and lf_b == lf_a, "eol 变了！"
    open(P2, "wb").write(out)
    after = hashlib.sha256(open(P2, "rb").read()).hexdigest()
    print("    → after %s  (delta %+d)  eol OK" % (after[:16], len(out) - len(raw)))
else:
    print("    ★ 命中数不为 1 ⇒ 跳过")
