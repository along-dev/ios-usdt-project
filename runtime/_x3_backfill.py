# -*- coding: utf-8 -*-
"""给 4 个新脚本补编码头（X3 规则的回溯补齐）。

★ 规则（X3）：
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
  import os, sys
  os.environ.setdefault("PYTHONIOENCODING", "utf-8")
  try:
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
      sys.stderr.reconfigure(encoding="utf-8", errors="replace")
  except Exception:
      pass

★ 插入位置：**在 `from __future__ import ...` 之后**（若有），
  否则在首个 import 块之前。
★ 幂等：已有真编码代码的脚本跳过。
"""
import io
import os
import re
import sys

D = IOS_ROOT + r"\_integration\_fix_work"
TARGETS = [
    "verify_d4c1_totp_secret.py",
    "verify_d4c2_credentials.py",
    "verify_manifest_scope.py",
    "verify_x4_unreproduced.py",
]

HEADER = '''import os
import sys

# ★ X3：本脚本自带 UTF-8 输出（P-10）
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

'''

# 真编码代码的判据（正则，非字符串包含 —— 避免 X3 的假阴性）
RE_ENV = re.compile(r"os\.environ\.setdefault\(\s*[\"']PYTHONIOENCODING[\"']")
RE_RECONF = re.compile(r"sys\.(stdout|stderr)\.reconfigure\(")


def has_real_encoding(src):
    return bool(RE_ENV.search(src) and RE_RECONF.search(src))


for fn in TARGETS:
    p = os.path.join(D, fn)
    if not os.path.isfile(p):
        print("  [缺失] %s" % fn)
        continue
    raw = open(p, "rb").read()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    eol = b"\r\n" if crlf > 0 and lf == 0 else b"\n"
    src = raw.decode("utf-8", "replace")

    if has_real_encoding(src):
        print("  [跳过] %s（已有真编码代码）" % fn)
        continue

    lines = src.split("\n")
    # 找到插入点：__future__ 之后，或首个 import/from 之前
    ins = None
    for i, l in enumerate(lines):
        if l.strip().startswith("from __future__"):
            ins = i + 1
            break
    if ins is None:
        for i, l in enumerate(lines):
            st = l.strip()
            if st.startswith("import ") or st.startswith("from "):
                ins = i
                break
    if ins is None:
        # 找 docstring 结束
        for i, l in enumerate(lines):
            if i > 0 and (l.strip().startswith('"""') or l.strip().startswith("'''")):
                ins = i + 1
                break
    if ins is None:
        print("  ★ 无法定位插入点: %s" % fn)
        continue

    new_lines = lines[:ins] + HEADER.rstrip("\n").split("\n") + lines[ins:]
    new_src = "\n".join(new_lines)
    out = new_src.encode("utf-8")
    if eol == b"\r\n":
        out = out.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    open(p, "wb").write(out)
    print("  ✅ 已补编码头: %s（插入于第 %d 行后）" % (fn, ins))
