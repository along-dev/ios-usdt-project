# -*- coding: utf-8 -*-
"""T61 · V2 保义判据的独立复算：三集合（中文字面/字符串/数值）＋「排除 import type 行」规则的健全性。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io, re

CJK = re.compile(r"[\u4e00-\u9fff]")
PAIRS = [
    ("先例 balance-init", r"E:\IOS源码1\server\src\schedules\balance-init.ts",
     USDT_ROOT + r"\02-backend-node\src_restored\schedules\balance-init.js"),
    ("本件 balance-refresh", r"E:\IOS源码1\server\src\schedules\balance-refresh.ts",
     USDT_ROOT + r"\02-backend-node\src_restored\schedules\balance-refresh.js"),
]
# 基准里的 tron/eth 件（USDT 侧未移植，不参与）


def scan(path):
    txt = io.open(path, encoding="utf-8").read()
    lines = txt.splitlines()
    strs, nums, cmt_n = set(), set(), 0
    importtype_lits, runtime_import_lits = set(), set()
    n_importtype, n_runtime_import = 0, 0
    for ln in lines:
        s = ln.strip()
        code = re.sub(r"//.*$", "", ln)
        lits = re.findall(r"'([^']*)'", code)
        if re.match(r"^import\s+type\b", s):
            n_importtype += 1
            importtype_lits |= set(lits)
        elif re.match(r"^import\b", s):
            n_runtime_import += 1
            runtime_import_lits |= set(lits)
        for m in lits:
            strs.add(m)
        for m in re.findall(r"(?<![\w.])(\d+\.?\d*(?:e-?\d+)?)", code):
            nums.add(m)
        if s.startswith("//") and CJK.search(s):
            cmt_n += 1
    return dict(strs=strs, nums=nums, cmt=cmt_n, imp_lits=importtype_lits,
                rt_lits=runtime_import_lits, n_imp=n_importtype, n_rt=n_runtime_import)


for label, ts, js in PAIRS:
    t, j = scan(ts), scan(js)
    print("== %s ==" % label)
    print("  .ts: 中文注释 %d 条 | 字符串 %d | 数值 %s | import type 行 %d | 运行时 import 行 %d"
          % (t["cmt"], len(t["strs"]), sorted(t["nums"]), t["n_imp"], t["n_rt"]))
    print("  .js: 中文注释 %d 条 | 字符串 %d | 数值 %s | import type 行 %d | 运行时 import 行 %d"
          % (j["cmt"], len(j["strs"]), sorted(j["nums"]), j["n_imp"], j["n_rt"]))
    print("  字符串丢失(未排除 import type):", sorted(t["strs"] - j["strs"]) or "无")
    print("  ★ 排除 import type 行字面量后，丢失:", sorted(t["strs"] - j["strs"] - t["imp_lits"]) or "无")
    print("  数值丢失:", sorted(t["nums"] - j["nums"]) or "无")
    print("  ★ 被排除的字面量恰在 import type 行上?",
          "是" if (t["strs"] - j["strs"]) <= t["imp_lits"] else "★否（有非 import-type 的丢失！）")
    print("  ★ 被排除的字面量是否也在<运行时 import>上（=排除无风险）:",
          sorted((t["strs"] - j["strs"]) & t["rt_lits"]) or "（无交集）")
    print()
