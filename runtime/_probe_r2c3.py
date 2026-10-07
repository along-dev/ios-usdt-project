# -*- coding: utf-8 -*-
"""R2-C3 取证：三个残留目录是否被引用 + 排除清单在哪。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re

DIRS = [".verify_tmp_storage", ".verify_tmp_storage_ds", ".rt_storage"]

print("=== 1) 谁引用这三个目录名？ ===")
ROOTS = [USDT_ROOT, IOS_ROOT + r"\_integration\_fix_work"]
hits = {d: [] for d in DIRS}
for root in ROOTS:
    for dp, dn, fns in os.walk(root):
        dn[:] = [d for d in dn if d not in ("node_modules", ".git")]
        for fn in fns:
            if not fn.endswith((".js", ".mjs", ".cjs", ".json", ".md", ".ps1", ".py", ".yaml", ".yml", ".gitignore")):
                continue
            p = os.path.join(dp, fn)
            try:
                if os.path.getsize(p) > 3 * 1024 * 1024:
                    continue
                s = io.open(p, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            for d in DIRS:
                if d in s:
                    # 排除"自身目录内文件"的自我提及
                    if os.path.normcase(os.path.normpath(os.path.dirname(p))).endswith(os.path.normcase(d)):
                        continue
                    hits[d].append(os.path.relpath(p, root))

for d in DIRS:
    print("  %-26s 被 %d 个文件提及" % (d, len(hits[d])))
    for f in sorted(set(hits[d]))[:8]:
        print("      ", f)

print("")
print("=== 2) 排除清单候选（.gitignore / .npmignore / README / 排除清单文件）===")
BASE = USDT_ROOT + r"\02-backend-node"
for fn in (".gitignore", ".npmignore", ".dockerignore", "README.md", "README_CN.md"):
    p = os.path.join(BASE, fn)
    print("  %-18s %s" % (fn, "存在（%d B）" % os.path.getsize(p) if os.path.isfile(p) else "不存在"))

print("")
print("=== 3) 全仓找 exclude / 排除 / ignore 相关文件 ===")
for root in [USDT_ROOT + r"\09-docs", USDT_ROOT + r"\02-backend-node", IOS_ROOT + r"\_integration"]:
    for dp, dn, fns in os.walk(root):
        dn[:] = [d for d in dn if d not in ("node_modules", ".git")]
        for fn in fns:
            low = fn.lower()
            if "exclude" in low or "排除" in fn or "ignor" in low:
                print("  ", os.path.join(dp, fn).replace(USDT_ROOT, "…").replace(IOS_ROOT, "…"))
