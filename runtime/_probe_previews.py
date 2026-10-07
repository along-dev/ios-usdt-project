# -*- coding: utf-8 -*-
"""探针：预览图与落地页静态资源在磁盘上的位置。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import os

ROOT = USDT_ROOT

print("=== 1) 搜 template-previews 目录 ===")
hits = 0
for base in [ROOT, IOS_ROOT]:
    for dp, dn, fns in os.walk(base):
        dn[:] = [d for d in dn if d not in (".git", "node_modules", "__pycache__")]
        if os.path.basename(dp) == "template-previews":
            hits += 1
            print("  [DIR] %s  (%d 文件)" % (dp, len(fns)))
            for f in fns[:8]:
                print("      ", f)
if not hits:
    print("  ★ 未找到 template-previews 目录")

print("")
print("=== 2) 搜 vodex.png / kiss.png 等预览图 ===")
names = {"vodex.png", "kiss.png", "ykluo7.png", "playstore.png", "elef.png", "bolt.png"}
found = 0
for base in [ROOT, IOS_ROOT]:
    for dp, dn, fns in os.walk(base):
        dn[:] = [d for d in dn if d not in (".git", "node_modules", "__pycache__")]
        for f in fns:
            if f in names:
                found += 1
                print("  %8d B  %s" % (os.path.getsize(os.path.join(dp, f)),
                                       os.path.join(dp, f)))
                if found > 12:
                    break
        if found > 12:
            break
if not found:
    print("  ★ 未找到任何预览图")

print("")
print("=== 3) 搜 landing-pages 目录 ===")
hits = 0
for base in [ROOT, IOS_ROOT]:
    for dp, dn, fns in os.walk(base):
        dn[:] = [d for d in dn if d not in (".git", "node_modules", "__pycache__")]
        if os.path.basename(dp) == "landing-pages":
            hits += 1
            subs = [d for d in os.listdir(dp) if os.path.isdir(os.path.join(dp, d))]
            print("  [DIR] %s  (%d 子目录)" % (dp, len(subs)))
            for sd in subs[:10]:
                print("      ", sd)
if not hits:
    print("  ★ 未找到 landing-pages 目录")

print("")
print("=== 4) 04-landing 的资产目录 ===")
L = os.path.join(ROOT, "04-landing")
if os.path.isdir(L):
    for e in sorted(os.listdir(L)):
        p = os.path.join(L, e)
        if os.path.isdir(p):
            n = sum(len(f) for _, _, f in os.walk(p))
            print("  %-14s %d 文件" % (e, n))
