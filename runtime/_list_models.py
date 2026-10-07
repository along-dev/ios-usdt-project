# -*- coding: utf-8 -*-
"""列出 model/app 的全部 struct 与 TableName，用于 RegisterTables 的准确类型名。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re

root = USDT_ROOT + r"\01-backend-go\model\app"
if not os.path.isdir(root):
    print("  [目录不存在] %s" % root)
    raise SystemExit

PAT_STRUCT = re.compile(r"^type\s+(\w+)\s+struct", re.M)
PAT_TABLE = re.compile(
    r"func\s+\([^)]*?\*?(\w+)\)\s+TableName\(\)\s+string\s*\{\s*return\s+\"([^\"]+)\""
)

print("=== model/app 的 struct 与表名 ===")
allst = []
for f in sorted(os.listdir(root)):
    if not f.endswith(".go"):
        continue
    p = os.path.join(root, f)
    s = io.open(p, encoding="utf-8", errors="replace").read()
    structs = PAT_STRUCT.findall(s)
    tables = {m[0]: m[1] for m in PAT_TABLE.findall(s)}
    for st in structs:
        tn = tables.get(st, "?")
        allst.append((f, st, tn))
        print("  %-28s %-26s table=%s" % (f, st, tn))

print("")
print("  总 struct 数:", len(allst))
print("")
print("=== 有 TableName 的（推荐用于 AutoMigrate）===")
for f, st, tn in allst:
    if tn != "?":
        print("  app.%-26s -> %s" % (st, tn))
