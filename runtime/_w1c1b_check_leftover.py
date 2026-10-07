# -*- coding: utf-8 -*-
"""
J4 复核器：检查指定文件中是否残留已知占位符。
★ 独立于 build_unified.ps1 的第三方复核（避免"自己验自己"）。

用法：python _w1c1b_check_leftover.py <文件或目录> [...]
输出：每个文件一行 FOUND/LEFTOVER；末行 LEFTOVER=<总命中数>
"""
from __future__ import annotations

import os
import sys

PLACEHOLDERS = ["__C2_ENDPOINT__", "__RCE_MAX_ATTEMPTS__"]


def check_file(p: str) -> int:
    try:
        with open(p, "rb") as f:
            text = f.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  [skip] {p}: {e}")
        return 0
    hits = 0
    for ph in PLACEHOLDERS:
        c = text.count(ph)
        if c:
            hits += c
            print(f"  [HIT] {p} :: {ph} x{c}")
    print(f"  [{'LEFTOVER' if hits else 'CLEAN'}] {os.path.basename(p)}  hits={hits}")
    return hits


def main(argv):
    targets = []
    for a in argv:
        if os.path.isdir(a):
            for dp, _, fns in os.walk(a):
                targets += [os.path.join(dp, fn) for fn in fns]
        else:
            targets.append(a)

    total = sum(check_file(p) for p in targets)
    print(f"SLOTS_CHECKED={len(targets)}")
    print(f"LEFTOVER={total}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
