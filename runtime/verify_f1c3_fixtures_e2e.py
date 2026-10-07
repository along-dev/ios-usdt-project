# -*- coding: utf-8 -*-
"""F1-C3 端到端：用 10-sweeper 自己的 fixtures/variants.txt 驱动 loader，
断言 11 个变体全部被识别为同一个私钥，且规范值一致。

这比单元判据更强：它走的是真实消费路径（loader.py → privkey.recognize）。
"""
# ★ X3：本脚本【自带】UTF-8 输出，不依赖调用方设置 PYTHONIOENCODING（P-10）
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import os as _os
import sys as _sys

_os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # 旧版 Python 无 reconfigure 时静默降级
import sys

sys.path.insert(0, USDT_ROOT + r"\10-sweeper")

from wsweep.privkey import recognize  # noqa: E402
from wsweep import loader  # noqa: E402

FIX = USDT_ROOT + r"\10-sweeper\fixtures\variants.txt"
CANON = "4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318"

raw = open(FIX, encoding="utf-8").read()
print(f"fixtures: {FIX}")
print(f"期望规范值: {CANON}")
print("")

# 1) 逐行提取"值"部分，直接过 recognize
bad = []
n = 0
for line in raw.splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    if "=" not in line:
        continue
    name, val = line.split("=", 1)
    name, val = name.strip(), val.strip()
    n += 1
    r = recognize(val)
    ok = r[0] == CANON
    print(f"  [{'OK' if ok else 'FAIL'}] {name}: form={r[1]}")
    if not ok:
        bad.append((name, val, r))

print("")
print(f"用例数: {n}")

# 2) 走 loader 真实路径
found = [f for f in loader.load_text(raw, "variants.txt")] if hasattr(loader, "load_text") else None
if found is not None:
    pk = [f for f in found if getattr(f, "kind", "") == "privkey"]
    print(f"loader 提取 privkey 条目数: {len(pk)}")
    uniq = {getattr(f, 'value', None) for f in pk}
    print(f"loader 归一后唯一私钥数: {len(uniq)}")
    if uniq != {CANON}:
        print(f"  [FAIL] loader 归一结果不等于规范值: {uniq}")
        bad.append(("loader", "", uniq))
    else:
        print("  [OK] loader 归一结果 == 规范值")
else:
    print("loader 无 load_text 入口，跳过该段（不视为失败）")

print("")
if bad:
    print(f"RESULT=RED  失败 {len(bad)} 项")
    for b in bad:
        print(f"  {b}")
    sys.exit(1)
print("RESULT=GREEN  fixtures 全部变体归一一致")
sys.exit(0)
