# -*- coding: utf-8 -*-
"""T62 · V3 保义对照：基准判定段 vs 本模块（中文注释/字符串字面量/数值常量）。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io, re, sys

CJK = re.compile(r'[\u4e00-\u9fff]')
BASE = r"E:\IOS源码1\server\src\core\collect\auto-collect.ts"
MINE = USDT_ROOT + r"\02-backend-node\src_restored\core\collect\auto-collect-judge.js"

base = io.open(BASE, encoding="utf-8").read().splitlines()
mine = io.open(MINE, encoding="utf-8").read().splitlines()

# 基准「判定段」= 行 60..190（shouldCollectTron → checkEthGas 结束）；L192+ 为执行侧，排除
seg = base[59:190]


def stats(lines, lo=1):
    cmt, strs, nums = [], set(), set()
    inblk = False
    for i, ln in enumerate(lines, lo):
        s = ln.strip()
        if s.startswith("/*") or inblk:
            if CJK.search(ln):
                cmt.append((i, s[:70]))
            inblk = ("*/" not in ln)
            continue
        if "//" in ln and CJK.search(ln.split("//", 1)[1]):
            cmt.append((i, ("//" + ln.split("//", 1)[1])[:70]))
        code = re.sub(r"//.*$", "", ln)
        for m in re.findall(r"'([^']*)'", code):
            strs.add(m)
        for m in re.findall(r"(?<![\w.])(\d+\.?\d*(?:e-?\d+)?)", code):
            nums.add(m)
    return cmt, strs, nums


bc, bs, bn = stats(seg, 60)
mc, ms, mn = stats(mine, 1)

print("== 基准判定段（L60-L190）==")
print("  中文注释 %d 条 | 字符串 %s | 数值 %s" % (len(bc), sorted(bs), sorted(bn)))
print("== 本模块 ==")
print("  中文注释 %d 条 | 字符串 %s | 数值 %s" % (len(mc), sorted(ms), sorted(mn)))
print()
print("字符串：基准有而我无 =", sorted(bs - ms) or "无")
print("数值  ：基准有而我无 =", sorted(bn - mn) or "无")
print()
print("== 基准判定段的中文注释逐条 ==")
for i, t in bc:
    print("  L%-4d %s" % (i, t))
