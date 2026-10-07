# -*- coding: utf-8 -*-
"""T1：更正 需求文档.md 的 P1-1/P1-2 过期登记。

★ 二进制读写，零换行转换（P-36）。
"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib
import io
import os

P = USDT_ROOT + r"\09-docs\analysis\需求文档.md"

OLD_1 = "| P1-1 | `rce_loader.js` 阶段状态机整表失效（方案称 1721 行，实际 259 行） | 无法据此开发 | 二期 |"
NEW_1 = ("| P1-1 | ~~`rce_loader.js` 阶段状态机整表失效~~ **❌ 登记有误** —— 行号**全部正确**"
         "（属 `src_recon/mirror/` 副本，**1,721 行**）；产物用的是 `darksword/` 的 **260 行旧开发版**"
         "（实测 `pe_ready`/`chainCkFinish`/`stage1_progress`/`phase` 计数**全为 0**） | — | "
         "**✅ 已澄清（二期无需做）** |")

OLD_2 = "| P1-2 | `sbx1_main.js` 行号全部错位 | 文档不可信 | 二期 |"
NEW_2 = ("| P1-2 | ~~`sbx1_main.js` 行号全部错位~~ **⚠️ 表述不准** —— 根因是**两份不同文件**"
         "（`darksword/` **6,862 行** vs `src_recon/mirror/` **7,812 行**，sha256 不同），"
         "偏移 **+52**（`calloc()` 处 **+169**）；引用属 `src_recon`，**行号本身正确** | — | "
         "**✅ 已修（加来源标注）** |")

raw = open(P, "rb").read()
before = hashlib.sha256(raw).hexdigest()
print("  base sha256: %s" % before)
print("  base bytes : %d" % len(raw))

src = raw.decode("utf-8")

# ★ 使用二进制替换（对 bytes 操作，零换行转换）
b1 = OLD_1.encode("utf-8")
b2 = OLD_2.encode("utf-8")

n1 = raw.count(b1)
n2 = raw.count(b2)
print("  OLD_1 命中: %d" % n1)
print("  OLD_2 命中: %d" % n2)

if n1 != 1 or n2 != 1:
    print("  ★ 命中数不为 1 ⇒ abort")
    raise SystemExit(1)

out = raw.replace(b1, NEW_1.encode("utf-8")).replace(b2, NEW_2.encode("utf-8"))

# 保形核对
crlf_b = raw.count(b"\r\n")
crlf_a = out.count(b"\r\n")
lf_b = raw.count(b"\n") - crlf_b
lf_a = out.count(b"\n") - crlf_a
print("  eol 保持: CRLF %d→%d, LONE_LF %d→%d" % (crlf_b, crlf_a, lf_b, lf_a))
assert crlf_b == crlf_a and lf_b == lf_a, "eol 变了！"

open(P, "wb").write(out)
after = hashlib.sha256(open(P, "rb").read()).hexdigest()
print("  after sha256: %s" % after)
print("  after bytes : %d  (delta %+d)" % (len(out), len(out) - len(raw)))
print("  ✅ 已更正")
