# -*- coding: utf-8 -*-
"""T8：P1-7 收口（manifest size 已修）—— 更正两处文档。

★ 二进制读写，零换行转换（P-36）。
★ eol 断言：CRLF 数 + LONE_CR 数不变（P-37）。
"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib

ROOT = USDT_ROOT


def eol_stats(b):
    crlf = b.count(b"\r\n")
    lone_lf = b.count(b"\n") - crlf
    lone_cr = b.count(b"\r") - crlf
    return crlf, lone_lf, lone_cr


EDITS = [
    # (文件, old, new, 标签)
    (
        ROOT + r"\09-docs\analysis\需求文档.md",
        "| **P1-7** | **manifest 14 条 entry 的 size 与磁盘不符** | **容器构造偏移错误 → 坏数据** | **一期（已定位，处置=以磁盘为准）** |",
        "| **P1-7** | ~~manifest 14 条 entry 的 size 与磁盘不符~~（**14 条 `entry3_type0x07.bin`**：manifest=44 / 磁盘=49） | 容器构造偏移错误 → 坏数据 | "
        "**✅ 已修（2026-09-27；判据 `verify_manifest_sizes.py` 实测 91/91 一致、0 不符）**——原裁决「以磁盘为准」得到印证（T8 收口） |",
        "T8-1 需求文档 P1-7",
    ),
    (
        ROOT + r"\09-docs\analysis\问题登记册.md",
        "| 4 | manifest size（P1-7） | **以磁盘为准** | `待编码` |",
        "| 4 | manifest size（P1-7） | ~~以磁盘为准~~ **manifest 已修为 49** | **✅ 已完成**（2026-09-27 修复；T8 复验 91/91 一致） |",
        "T8-2 登记册 :450",
    ),
    (
        ROOT + r"\09-docs\analysis\问题登记册.md",
        "## P1-7 manifest 与磁盘大小不符　`已定位（处置已定）`",
        "## P1-7 manifest 与磁盘大小不符　`✅ 已修复并验证（T8，2026 本轮）`",
        "T8-3 登记册 :98",
    ),
]

for path, old, new, label in EDITS:
    raw = open(path, "rb").read()
    before = hashlib.sha256(raw).hexdigest()
    n = raw.count(old.encode("utf-8"))
    print("  [%s] 命中: %d  (base %s)" % (label, n, before[:16]))
    if n != 1:
        print("    ★ 命中数不为 1 ⇒ 跳过")
        continue
    out = raw.replace(old.encode("utf-8"), new.encode("utf-8"))
    cb, lb, crb = eol_stats(raw)
    ca, la, cra = eol_stats(out)
    ok = (cb == ca and crb == cra)
    print("    eol: CRLF %d→%d  LONE_LF %d→%d  LONE_CR %d→%d  %s"
          % (cb, ca, lb, la, crb, cra, "✅ OK" if ok else "★ 风格变了"))
    if not ok:
        print("    ★ 跳过（eol 风格被改）")
        continue
    open(path, "wb").write(out)
    after = hashlib.sha256(open(path, "rb").read()).hexdigest()
    print("    → after %s  (delta %+d)" % (after[:16], len(out) - len(raw)))
