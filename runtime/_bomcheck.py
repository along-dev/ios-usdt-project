# -*- coding: utf-8 -*-
"""检查 build_unified.ps1 的 BOM / 行尾 / 是否含非 UTF-8 序列。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import sys

p = IOS_ROOT + r"\_integration\build_unified.ps1"
bak = IOS_ROOT + r"\_integration\build_unified.ps1.bak_w1c1b"

for label, path in (("CURRENT", p), ("BACKUP", bak)):
    with open(path, "rb") as f:
        b = f.read()
    bom = b.startswith(b"\xef\xbb\xbf")
    crlf = b.count(b"\r\n")
    lf = b.count(b"\n")
    try:
        b.decode("utf-8")
        dec = "utf-8 OK"
    except UnicodeDecodeError as e:
        dec = f"utf-8 FAIL: {e}"
    print(f"{label}: bytes={len(b)} BOM={bom} CRLF={crlf} LF={lf} decode={dec}")
    print(f"  head={b[:24]!r}")
