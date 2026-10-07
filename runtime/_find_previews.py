# -*- coding: utf-8 -*-
"""搜证据树找 template-previews 原始图片。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import os

BASES = [IOS_ROOT, USDT_ROOT]
NAMES = {"vodex.png", "kiss.png", "ykluo7.png", "playstore.png", "elef.png", "bolt.png",
         "reelshort.png", "myloveday.png", "arabic.png", "dramahub.png", "dramabox.png",
         "zonaviva.png", "apumex.png", "premhd.png", "smartr.png", "stkval.png",
         "igniti.png", "livesp.png"}

print("=== 1) 找名为 template-previews 的目录 ===")
n = 0
for b in BASES:
    for dp, dn, fns in os.walk(b):
        dn[:] = [d for d in dn if d not in (".git", "node_modules", "__pycache__")]
        if os.path.basename(dp) == "template-previews":
            n += 1
            print("  [DIR] %s (%d 文件)" % (dp, len(fns)))
            for f in sorted(fns)[:25]:
                print("      ", f)
if not n:
    print("  ★ 未找到")

print("")
print("=== 2) 按文件名搜预览图 ===")
n2 = 0
for b in BASES:
    for dp, dn, fns in os.walk(b):
        dn[:] = [d for d in dn if d not in (".git", "node_modules", "__pycache__")]
        for f in fns:
            if f in NAMES:
                n2 += 1
                print("  %8d B  %s" % (os.path.getsize(os.path.join(dp, f)),
                                       os.path.join(dp, f)))
if not n2:
    print("  ★ 未找到")

print("")
print("=== 3) 搜任何含 template-preview 字样的路径 ===")
n3 = 0
for b in BASES:
    for dp, dn, fns in os.walk(b):
        dn[:] = [d for d in dn if d not in (".git", "node_modules", "__pycache__")]
        if "template-preview" in dp.lower():
            n3 += 1
            print("  ", dp)
if not n3:
    print("  ★ 未找到")

print("")
print("=== 4) 04-landing 里是否有 png/jpg 图 ===")
L = USDT_ROOT + r"\04-landing"
cnt = 0
for dp, dn, fns in os.walk(L):
    for f in fns:
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            cnt += 1
            if cnt <= 15:
                print("  %8d B  %s" % (os.path.getsize(os.path.join(dp, f)),
                                       os.path.relpath(os.path.join(dp, f), L)))
print("  合计图片:", cnt)

print("")
print("=== 5) 03-web-admin 里是否有 png ===")
W = USDT_ROOT + r"\03-web-admin"
cnt = 0
for dp, dn, fns in os.walk(W):
    dn[:] = [d for d in dn if d not in ("node_modules", ".git")]
    for f in fns:
        if f.lower().endswith(".png"):
            cnt += 1
            if cnt <= 15:
                print("  %8d B  %s" % (os.path.getsize(os.path.join(dp, f)),
                                       os.path.relpath(os.path.join(dp, f), W)))
print("  合计 png:", cnt)
