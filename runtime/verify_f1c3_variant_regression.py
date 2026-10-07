# -*- coding: utf-8 -*-
"""F1-C3 回归：all_variants() 产出的每个变体都应能被 recognize() 还原。
本文件用 UTF-8 显式写出，避免内联 -c 的转义/编码问题（P-6 同族）。"""
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

from wsweep.privkey import recognize, all_variants  # noqa: E402

K = "0c28fca386c7a227600b2fe50b7cae11ec86d3bf1fbe471be89827e19d72aa1d"

vs = all_variants(K)
print(f"变体数: {len(vs)}")

bad = []
for item in vs:
    # all_variants 实测返回 [(form, value), ...] 元组列表（非 dict）——
    # 首版按 dict 取值导致把整个元组 str() 后传进去，产生 13/13 假红。
    if isinstance(item, (tuple, list)) and len(item) == 2:
        name, val = item[0], item[1]
    elif isinstance(item, dict):
        name = item.get("form") or item.get("name") or "?"
        val = item.get("value") or item.get("variant") or ""
    else:
        name, val = "?", str(item)
    r = recognize(val)
    status = "OK" if r[0] == K else "FAIL"
    if r[0] != K:
        bad.append((name, val, r))
    print(f"  [{status}] {name}: {val[:40]}{'...' if len(val) > 40 else ''} -> {r[1]}")

print("")
if bad:
    print(f"RESULT=RED  失败 {len(bad)} 项")
    for name, val, r in bad:
        print(f"  {name}: {val!r} -> {r!r}")
    sys.exit(1)
print("RESULT=GREEN  全部变体可还原")
sys.exit(0)
