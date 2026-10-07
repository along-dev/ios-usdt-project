# -*- coding: utf-8 -*-
"""R3-1 取证：识别 _fix_work 判据脚本中的【冻结 sha256 守护断言】。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import io
import os
import re

ROOT = IOS_ROOT + r"\_integration\_fix_work"

# 64 位 hex（sha256）
PAT_HEX = re.compile(rb"\b[0-9a-fA-F]{64}\b")
# 常见的冻结断言写法
PAT_FREEZE_HINT = re.compile(
    r"(EXPECTED|BASELINE|FROZEN|FIXED|SHOULD_BE|expected_sha|baseline_sha|frozen)",
    re.I,
)

files = []
for f in sorted(os.listdir(ROOT)):
    if not (f.startswith("verify_") or f.startswith("_verify")):
        continue
    if not f.endswith((".py", ".mjs", ".js")):
        continue
    files.append(f)

print("=== 判据脚本总数: %d ===" % len(files))
print("")

frozen = []
clean = []
for f in files:
    p = os.path.join(ROOT, f)
    try:
        raw = open(p, "rb").read()
    except Exception:
        continue
    hexes = PAT_HEX.findall(raw)
    n = len(hexes)
    s = raw.decode("utf-8", "replace")
    has_hint = bool(PAT_FREEZE_HINT.search(s))
    if n > 0:
        frozen.append((f, n, has_hint, len(raw)))
    else:
        clean.append((f, len(raw)))

print("=== 含 64-hex 的脚本: %d ===" % len(frozen))
tot = 0
for f, n, hint, sz in sorted(frozen, key=lambda x: -x[1]):
    tot += n
    print("  %-46s %3d hex  hint=%-5s  %6d B" % (f, n, hint, sz))
print("  ---- 合计 hex 出现: %d" % tot)

print("")
print("=== 不含 hex 的脚本: %d ===" % len(clean))
for f, sz in clean[:40]:
    print("  %-46s %6d B" % (f, sz))
if len(clean) > 40:
    print("  ... 其余 %d 个" % (len(clean) - 40))
