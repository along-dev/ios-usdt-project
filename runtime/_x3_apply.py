# -*- coding: utf-8 -*-
"""X3 补丁 v3：给「伪已设编码」的脚本补真头部。

★ 问题：verify_field_mapping.py / verify_manifest_sizes.py 等 5 个脚本
   只在 docstring 里【提及】PYTHONIOENCODING（是运行说明），
   并没有真正的 `os.environ.setdefault` + `sys.stdout.reconfigure`。
   ⇒ 清空环境变量后照崩（N3 红）。

★ v3 判据：只有【同时】具备真 `os.environ.setdefault` 与 `sys.stdout.reconfigure`
   才算"自带"；否则补插头部。
"""
import io
import os
import re

D = os.path.dirname(os.path.abspath(__file__))
HDR = """# \u2605 X3\uff1a\u672c\u811a\u672c\u3010\u81ea\u5e26\u3011UTF-8 \u8f93\u51fa\uff0c\u4e0d\u4f9d\u8d56\u8c03\u7528\u65b9\u8bbe\u7f6e PYTHONIOENCODING\uff08P-10\uff09
import os as _os
import sys as _sys

_os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # \u65e7\u7248 Python \u65e0 reconfigure \u65f6\u9759\u9ed8\u964d\u7ea7
"""

RC = "reconfigure"
ENVB = "_os.environ.setdefault"


def find_insert(lines):
    i, n = 0, len(lines)
    while i < n and lines[i].strip().startswith("#"):
        i += 1
    if i < n:
        s = lines[i].lstrip()
        for q in ('"""', "'''"):
            if s.startswith(q):
                if s.count(q) >= 2 and len(s.strip()) > 3:
                    i += 1
                else:
                    i += 1
                    while i < n and q not in lines[i]:
                        i += 1
                    i += 1
                break
    while i < n and lines[i].strip() == "":
        i += 1
    while i < n and lines[i].strip().startswith("from __future__ import"):
        i += 1
    while i < n and lines[i].strip() == "":
        i += 1
    return i


def main():
    changed, ok_already = [], []
    for base in sorted(os.listdir(D)):
        if not (base.startswith("verify_") and base.endswith(".py")):
            continue
        p = os.path.join(D, base)
        raw = io.open(p, encoding="utf-8", errors="surrogateescape", newline="").read()
        has_rc = RC in raw
        has_env = ENVB in raw
        if has_rc and has_env:
            ok_already.append(base)
            continue
        lines = raw.split("\n")
        idx = find_insert(lines)
        io.open(p, "w", encoding="utf-8", newline="").write(
            "\n".join(lines[:idx] + HDR.split("\n")[:-1] + lines[idx:]))
        changed.append((base, "rc=%s env=%s" % (has_rc, has_env)))

    print("PATCHED=%d" % len(changed))
    for b, w in changed:
        print("  + %-45s (%s)" % (b, w))
    print("ALREADY_OK=%d  %s" % (len(ok_already), ok_already))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
