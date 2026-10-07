# -*- coding: utf-8 -*-
"""对照上游 seed 的 casbin 数据，生成 qk_e2e 的 seed（裁决 A）。

★ 只读上游（qk_t26_empty）的 casbin_rule，按其 (v1,v2) 组合
   映射到 qk_e2e 的角色语义：
     qk_e2e 888（超级管理员）← 上游 888 的全部（92 条）
     qk_e2e 9528（普通用户） ← 只取 GET（只读子集）
★ 不写入 DB：只生成 INSERT 语句到文件。
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import io
import subprocess

MYSQL = IOS_ROOT + r"\_integration\_fix_work\_toolchain\mariadb-11.4.4-winx64\bin\mysql.exe"


def q(db, sql):
    r = subprocess.run(
        [MYSQL, "-h", "127.0.0.1", "-P", "13306", "-u", "root", "-N", "-B",
         "--default-character-set=utf8mb4", db, "-e", sql],
        capture_output=True,
    )
    out = r.stdout.decode("utf-8", "replace")
    return [l.split("\t") for l in out.splitlines() if l.strip() and "WARNING" not in l]


print("=== 1) 上游 seed 的 casbin 列名 ===")
cols = q("qk_t26_empty", "SHOW COLUMNS FROM casbin_rule;")
print("  ", [c[0] for c in cols])

print("")
print("=== 2) 上游 888 的全部策略（应按 method 分组）===")
rows = q("qk_t26_empty",
         "SELECT v1, v2 FROM casbin_rule WHERE p_type='p' AND v0='888' ORDER BY v2, v1;")
print("  条数:", len(rows))
from collections import Counter
c = Counter(r[1] for r in rows)
print("  ", dict(c))

print("")
print("=== 3) 上游 sys_apis 条数 ===")
rows2 = q("qk_t26_empty", "SELECT path, method, api_group FROM sys_apis ORDER BY api_group, path;")
print("  条数:", len(rows2))

print("")
print("=== 4) 上游 sys_apis 与 888 策略的对应（应一致）===")
set_apis = {(r[0], r[1]) for r in rows2}
set_pol = {(r[0], r[1]) for r in rows}
print("  sys_apis 集合大小:", len(set_apis))
print("  888 策略集合大小:", len(set_pol))
print("  仅在 sys_apis:", len(set_apis - set_pol))
print("  仅在 888 策略:", len(set_pol - set_apis))

print("")
print("=== 5) qk_e2e 的路由数（我的 30-casbin-seed.sql 用了 111 条路由）===")
print("  上游 sys_apis 只有", len(rows2), "条 ⇒ 差异原因：上游是脚手架版路由")
print("  稍后需比对 qk_e2e 实际需要保护的路由")
