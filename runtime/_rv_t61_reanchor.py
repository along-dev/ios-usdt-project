# -*- coding: utf-8 -*-
"""T61 重锚 · 独立猎「第二个未登记的例外」：
基准 .ts（去类型语法） vs 新 .js —— 规范化后逐行 diff，人工分类每个差异。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io, re, difflib

TS = r"E:\IOS源码1\server\src\schedules\balance-refresh.ts"
JS = USDT_ROOT + r"\02-backend-node\src_restored\schedules\balance-refresh.js"


def norm(path, is_ts):
    out = []
    for raw in io.open(path, encoding="utf-8").read().splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("//# sourceMappingURL"):
            continue
        if is_ts and re.match(r"^import\s+type\b", s):
            continue                      # ★ 口径：import type 整行删（应消失）
        if is_ts and re.match(r"^(export\s+)?(interface|type)\s+\w+", s):
            continue                      # 类型声明整条删
        if s.startswith("//"):
            out.append(("C", s))          # 保留注释行以便对照
            continue
        # 去 TS 类型标注 / as 断言 / 参数类型
        t = re.sub(r"\bas\s+[A-Za-z_][\w.]*(<[^>]*>)?", "", s)
        t = re.sub(r":\s*[A-Za-z_][\w.]*(\[\])?(<[^>]*>)?(\s*\|\s*null)?", "", t)
        t = re.sub(r"<[A-Za-z_][\w,\s.]*>", "", t)
        t = re.sub(r"\s+", " ", t).strip()
        t = t.replace("export const", "const").replace("export async function", "async function")
        out.append(("K", t))
    return out


a = norm(TS, True)
b = norm(JS, False)
print("基准 .ts 规范化 %d 行 | 新 .js 规范化 %d 行" % (len(a), len(b)))
print("=" * 70)
ka = [t for _, t in a]
kb = [t for _, t in b]
for line in difflib.unified_diff(ka, kb, "baseline.ts(norm)", "new.js(norm)", lineterm="", n=2):
    print(line)
