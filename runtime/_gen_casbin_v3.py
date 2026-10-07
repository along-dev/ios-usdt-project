# -*- coding: utf-8 -*-
"""R2-2 · 从【运行时路由表】生成 casbin seed v3。

★ 权威源：Go 启动日志的 [GIN-debug] 行（运行时注册的真实路由）。
★ 比 router/*.go 的正则提取更准（能正确处理条件注册、组嵌套）。
★ 排除：/base/*、/app/*、/init/*、/uploads/*、/form-generator/*、/health
   —— 这些注册在 PublicGroup 或走 ServiceTokenAuth，不经 CasbinHandler。
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import io
import json
import re

LOG = IOS_ROOT + r"\_integration\_fix_work\_t26_run3.log"
OUT = USDT_ROOT + r"\07-db\migration\32-casbin-seed-v3.sql"

PAT = re.compile(r"\[GIN-debug\]\s+(GET|POST|PUT|DELETE|PATCH|HEAD)\s+(\S+)")
SKIP_PREFIX = ("/base/", "/app/", "/init/", "/uploads/", "/form-generator/", "/health", "/favicon")

routes = []
seen = set()
for l in io.open(LOG, encoding="utf-8", errors="replace").read().splitlines():
    m = PAT.search(l)
    if not m:
        continue
    method, path = m.group(1), m.group(2)
    if path.endswith("*filepath"):
        continue
    if any(path.startswith(s) for s in SKIP_PREFIX):
        continue
    # 去重（HEAD 与 GET 同路径时只留 GET）
    key = (path, method)
    if key in seen:
        continue
    seen.add(key)
    routes.append((path, method))

routes.sort()

print("=== 提取结果 ===")
print("  需保护路由:", len(routes))

# 按分组统计
from collections import Counter
g = Counter(p.split("/")[1] if "/" in p[1:] else p for p, m in routes)
print("  分组:", dict(g))

# ---- 生成 SQL ----
lines = []
lines.append("-- ============================================================================")
lines.append("-- R2-2 · casbin seed v3（★ 从【运行时路由表】生成）")
lines.append("-- ============================================================================")
lines.append("-- Owner 裁决 A：888（超级管理员）→ 全部；9528（普通用户）→ 只读 GET")
lines.append("--")
lines.append("-- ★ v3 与 v2 的区别：")
lines.append("--   v2 用 router/*.go 的【正则提取】⇒ 漏 20 条、方法不匹配 4 条；")
lines.append("--   v3 用 Go 启动日志的 [GIN-debug] 行 ⇒ 运行时【真实注册】的路由。")
lines.append("--")
lines.append("-- ★ 排除（不经 CasbinHandler）：")
lines.append("--   /base/*（PublicGroup 匿名）、/app/*（ServiceTokenAuth）、")
lines.append("--   /init/*（PublicGroup）、/uploads/*、/form-generator/*、/health")
lines.append("--")
lines.append("-- ★ 幂等：INSERT ... SELECT ... WHERE NOT EXISTS")
lines.append("-- ============================================================================")
lines.append("")
lines.append("-- ---- 步骤 1：sys_apis ----")
lines.append("INSERT INTO `sys_apis` (`created_at`, `updated_at`, `path`, `api_group`, `method`)")
lines.append("SELECT NOW(), NOW(), src.p, src.g, src.m FROM (")

rows = []
for i, (path, method) in enumerate(routes):
    grp = path.split("/")[1] if path.count("/") >= 2 else path.lstrip("/")
    kw = "SELECT" if i == 0 else "UNION ALL SELECT"
    rows.append("    %s '%s' AS p, '%s' AS g, '%s' AS m" % (kw, path, grp, method))
lines.append("\n".join(rows))
lines.append("  ) AS src")
lines.append(" WHERE NOT EXISTS (")
lines.append("     SELECT 1 FROM `sys_apis` a WHERE a.`path` = src.p AND a.`method` = src.m")
lines.append(" );")
lines.append("")
lines.append("SELECT '--- sys_apis 总数 ---' AS section;")
lines.append("SELECT COUNT(*) AS n FROM `sys_apis`;")
lines.append("")
lines.append("-- ---- 步骤 2：casbin_rule ----")
lines.append("-- 888：全部")
lines.append("INSERT INTO `casbin_rule` (`p_type`, `v0`, `v1`, `v2`)")
lines.append("SELECT 'p', '888', a.`path`, a.`method` FROM `sys_apis` a")
lines.append(" WHERE NOT EXISTS (")
lines.append("   SELECT 1 FROM `casbin_rule` c WHERE c.`p_type`='p' AND c.`v0`='888'")
lines.append("     AND c.`v1`=a.`path` AND c.`v2`=a.`method`);")
lines.append("")
lines.append("-- 9528：只读（GET）")
lines.append("INSERT INTO `casbin_rule` (`p_type`, `v0`, `v1`, `v2`)")
lines.append("SELECT 'p', '9528', a.`path`, a.`method` FROM `sys_apis` a")
lines.append(" WHERE a.`method`='GET' AND NOT EXISTS (")
lines.append("   SELECT 1 FROM `casbin_rule` c WHERE c.`p_type`='p' AND c.`v0`='9528'")
lines.append("     AND c.`v1`=a.`path` AND c.`v2`=a.`method`);")
lines.append("")
lines.append("SELECT '--- casbin_rule 统计 ---' AS section;")
lines.append("SELECT `v0` AS role, `v2` AS method, COUNT(*) AS n FROM `casbin_rule`")
lines.append(" WHERE `p_type`='p' GROUP BY `v0`, `v2` ORDER BY `v0`, `v2`;")
lines.append("")
lines.append("-- ---- 验收 ----")
lines.append("SELECT '--- 验收1：888 覆盖率 ---' AS section;")
lines.append("SELECT (SELECT COUNT(*) FROM `sys_apis`) AS apis_total,")
lines.append("       (SELECT COUNT(*) FROM `casbin_rule` WHERE `p_type`='p' AND `v0`='888') AS granted_888;")
lines.append("SELECT '--- 验收2：9528 只读 ---' AS section;")
lines.append("SELECT `v2` AS method, COUNT(*) AS n FROM `casbin_rule`")
lines.append(" WHERE `p_type`='p' AND `v0`='9528' GROUP BY `v2`;")
lines.append("SELECT '--- 验收3：无 1234 ---' AS section;")
lines.append("SELECT COUNT(*) AS n_1234 FROM `casbin_rule` WHERE `v0`='1234';")
lines.append("")

with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(lines))

print("")
print("  已写:", OUT)
print("  SQL 行数:", len(lines))
