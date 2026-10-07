# -*- coding: utf-8 -*-
"""
独立统计 Node 路由（python 直读，绕开 PowerShell Select-String 的怪行为）。
P-5：先用必然命中的样本证明量尺有效。
"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import os
import re

ROOT = USDT_ROOT + r"\02-backend-node\src_restored"
PAT = re.compile(r"fastify\.(get|post|put|delete)\(\s*'/api/([^']*)'")
# 宽松版：捕获整行内的路径（含模板串）

files = []
for dirpath, _dirnames, filenames in os.walk(ROOT):
    if "node_modules" in dirpath:
        continue
    for fn in filenames:
        if fn.endswith(".js"):
            files.append(os.path.join(dirpath, fn))

print(f".js 文件数: {len(files)}")

# ---- 量尺前置断言：先在【已知必含】的文件上验证 ----
known = os.path.join(ROOT, "plugins", "api", "middleware", "auth.js")
src_known = open(known, encoding="utf-8", errors="replace").read()
n_known = len(PAT.findall(src_known))
print(f"[量尺] auth.js 命中 = {n_known}  (预期 0：它用 addHook 而非路由注册)")

known2 = os.path.join(ROOT, "plugins", "api", "routes", "landing.js")
src_known2 = open(known2, encoding="utf-8", errors="replace").read()
n_known2 = len(PAT.findall(src_known2))
print(f"[量尺] landing.js 命中 = {n_known2}  (预期 5)")

if n_known2 == 0:
    print("量尺坏了：连已知文件都 0 命中")
    raise SystemExit(2)

# ---- 正式统计 ----
per_file = {}
all_paths = set()
total_lines = 0
for f in files:
    src = open(f, encoding="utf-8", errors="replace").read()
    hits = PAT.findall(src)
    if hits:
        per_file[os.path.relpath(f, ROOT)] = len(hits)
        total_lines += len(hits)
        for _m, p in hits:
            all_paths.add("/api/" + p)

print("")
print(f"总命中行数: {total_lines}")
print(f"唯一 /api 路径数: {len(all_paths)}")
print("")
print("Top 10 文件:")
for k, v in sorted(per_file.items(), key=lambda x: -x[1])[:10]:
    print(f"  {v}  {k}")

# ---- 三条 track 冲突复核 ----
print("")
print("三条 track 路径占用:")
for p in ("/api/track/start", "/api/track/heartbeat", "/api/track/click"):
    owners = [k for k in per_file if False]
    hit_files = []
    for f in files:
        src = open(f, encoding="utf-8", errors="replace").read()
        if f"'{p}'" in src:
            hit_files.append(os.path.relpath(f, ROOT))
    print(f"  {p} -> {hit_files}")
