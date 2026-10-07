# -*- coding: utf-8 -*-
"""给指定 .ps1 补 UTF-8 BOM（PS 5.1 无 BOM 时按 ANSI 读 → 中文路径乱码）。"""
import sys

def add_bom(p):
    with open(p, "rb") as f:
        b = f.read()
    if b.startswith(b"\xef\xbb\xbf"):
        print(f"ALREADY_BOM: {p}")
        return
    with open(p, "wb") as f:
        f.write(b"\xef\xbb\xbf" + b)
    print(f"BOM_ADDED: {p} ({len(b)} -> {len(b)+3} bytes)")

for p in sys.argv[1:]:
    add_bom(p)
