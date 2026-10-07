# -*- coding: utf-8 -*-
"""复核 T52第二段 · 变异实验：默认跑能否发现「分句器失灵」/「T53 口径回退」。
⚠️ 只 monkeypatch 内存中的函数对象，⛔ 不写盘、不改受审件。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import sys, io, os
sys.path.insert(0, IOS_ROOT + r"\_integration\_fix_work")
import verify_ad09_schema_migration_diff as A
import verify_migration_hygiene as H

def run_main(label, patch=None):
    orig = A._code_mask
    if patch: patch()
    sys.argv = ["verify_migration_hygiene.py"]          # ⛔ 不跑 --selftest
    buf = io.StringIO(); old = sys.stdout; sys.stdout = buf
    try:
        rc = H.main()
    finally:
        sys.stdout = old
        A._code_mask = orig
    out = buf.getvalue()
    a2 = [l for l in out.splitlines() if "[A2]" in l]
    a3 = [l for l in out.splitlines() if "[A3]" in l]
    res = [l for l in out.splitlines() if l.startswith("RESULT=")]
    print("── %s" % label)
    print("   退出码 =", rc, "（0=GREEN 1=RED）")
    for l in a2 + a3 + res: print("   ", l[:150])
    return rc

print("=== 基线（未变异）===")
run_main("基线")

print("\n=== M1：分句器全失灵（_code_mask 全标 trivia）===")
def m1():
    A._code_mask = lambda t: bytearray(len(t))
run_main("M1 全失灵", m1)

print("\n=== M2：把 /*!…*/ 退回当普通块注释（＝T53 口径回退）===")
def m2():
    orig = A._code_mask
    def patched(text):
        mask = orig(text)
        i = 0
        while True:
            i = text.find("/*!", i)
            if i < 0: break
            j = text.find("*/", i + 2)
            if j < 0: break
            for k in range(i, j + 2): mask[k] = 0
            i = j + 2
        return mask
    A._code_mask = patched
run_main("M2 T53 口径回退", m2)
