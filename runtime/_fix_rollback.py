# -*- coding: utf-8 -*-
"""修复 rollback.ps1：① 把被误替换的 `\\ = Test-Guards` 复原为 `$null = Test-Guards`
                  ② 把帮助文本里的 <commit> 改为 [commit]（PS 里 < 是保留符）"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib
import io

p = USDT_ROOT + r"\rollback.ps1"
raw = open(p, "rb").read()
print("  base:", hashlib.sha256(raw).hexdigest()[:16], "bytes:", len(raw))

s = raw.decode("utf-8")

# ① 修误替换
before1 = s.count("\\ = Test-Guards")
s = s.replace("\\ = Test-Guards", "$null = Test-Guards")
print("  修正误替换:", before1)

# ② 修 <commit>（PS 双引号内 < 是重定向保留符）
before2 = s.count("<commit>")
s = s.replace("<commit>", "[commit]")
print("  修正 <commit>:", before2)

out = s.encode("utf-8")
# 保 BOM
if not out.startswith(b"\xef\xbb\xbf"):
    out = b"\xef\xbb\xbf" + out

open(p, "wb").write(out)
print("  -> after:", hashlib.sha256(out).hexdigest()[:16], "bytes:", len(out))

# 复查
s2 = io.open(p, encoding="utf-8", errors="replace").read()
print("")
print("  复查：")
print("    '$null = Test-Guards':", s2.count("$null = Test-Guards"))
print("    残留 '\\\\ = Test-Guards':", s2.count("\\ = Test-Guards"))
print("    残留 '<commit>':", s2.count("<commit>"))
