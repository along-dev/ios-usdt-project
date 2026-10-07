# -*- coding: utf-8 -*-
"""R-06 取证：其余 5 类凭据的性质与暴露面（是否进交付）。"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re

ROOT = USDT_ROOT

# (2) 11-payment 明文口令
# (3) JWT
# (4) apidoc AccessKey/SecretKey
# (5) 06-android AES key
# (6) 05-ios AES key
TARGETS = [
    ("(2) 口令 HJAOxU46", "HJAOxU46"),
    ("(3) JWT 前缀 eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"),
    ("(4) AccessKey BlVnlKWzllSGLm47BkWahzRq", "BlVnlKWzllSGLm47BkWahzRq"),
    ("(4) SecretKey 0r3W6Br2y8HK9VGzm5J9HXDwopY0J7SqeN6yzYqM", "0r3W6Br2y8HK9VGzm5J9HXDwopY0J7SqeN6yzYqM"),
    ("(5) AES key 3e88e24c", "3e88e24cb730e0f1367a7d5f76d9427661e6c7fdc952c3e4d8f6d403b8585b7a"),
    ("(6) AES key b38fd1cc", "b38fd1ccd6570d8b3ce8edabd740e60d97e93a44fb27b35f2c54c473a37ce676"),
]

SKIP = {"node_modules", ".git", "__pycache__", ".vs"}

for label, needle in TARGETS:
    print("=== %s ===" % label)
    hits = []
    for dp, dn, fns in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in SKIP]
        for fn in fns:
            p = os.path.join(dp, fn)
            try:
                if os.path.getsize(p) > 20 * 1024 * 1024:
                    continue
                raw = open(p, "rb").read()
            except Exception:
                continue
            if needle.encode() in raw:
                hits.append(os.path.relpath(p, ROOT))
    print("  命中 %d 个文件:" % len(hits))
    for h in sorted(hits)[:10]:
        print("    ", h)
    if len(hits) > 10:
        print("     ... 还有 %d" % (len(hits) - 10))
    print("")

# 检查是否在 manifest 中
print("=== 是否在 _manifest.sha256 中 ===")
man = open(os.path.join(ROOT, "_manifest.sha256"), "rb").read().decode("utf-8-sig", "replace")
for label, needle in TARGETS:
    pass
for kw in ["privesc", "pw_login", "dash_net", "apidoc", "bdecrypt", "payload_cdn", "11-payment"]:
    n = man.count(kw)
    print("  manifest 含 '%s': %d 处" % (kw, n))
