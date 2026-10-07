# -*- coding: utf-8 -*-
"""T22 取证：bill 表结构 + Go 侧 /app/* 的既有实现模式。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import os
import re
import subprocess

ROOT = USDT_ROOT + r"\01-backend-go"
MYSQL = IOS_ROOT + r"\_integration\_fix_work\_toolchain\mariadb-11.4.4-winx64\bin\mysql.exe"


def q(sql):
    r = subprocess.run([MYSQL, "-h", "127.0.0.1", "-P", "13306", "-u", "root", "qk_e2e",
                        "-N", "-B", "--default-character-set=utf8mb4", "-e", sql],
                       capture_output=True, timeout=30)
    return r.stdout.decode("utf-8", "replace")


print("=== 1) bill 表结构 ===")
print(q("DESC bill;"))

print("=== 2) bill 表数据抽样（前 5 行）===")
print(q("SELECT * FROM bill LIMIT 5;"))

print("=== 3) bill 行数 ===")
print(q("SELECT COUNT(*) AS n FROM bill;"))

print("=== 4) Go 侧 /app/* 的路由注册 ===")
p = os.path.join(ROOT, "router", "app", "public.go")
if os.path.isfile(p):
    for i, l in enumerate(io.open(p, encoding="utf-8", errors="replace").read().splitlines(), 1):
        t = l.strip()
        if t and not t.startswith("//"):
            print("  %4d: %s" % (i, t[:120]))
else:
    print("  [缺失]")

print("")
print("=== 5) model 里是否有 bill 的 struct ===")
for dp, dn, fns in os.walk(os.path.join(ROOT, "model")):
    for f in fns:
        if not f.endswith(".go"):
            continue
        fp = os.path.join(dp, f)
        s = io.open(fp, encoding="utf-8", errors="replace").read()
        if re.search(r"bill|Bill", s):
            print("  %s" % os.path.relpath(fp, ROOT))
            for i, l in enumerate(s.splitlines(), 1):
                if re.search(r"bill|Bill", l):
                    print("    %4d: %s" % (i, l.strip()[:110]))
