"""
SQL 迁移脚本静态校验（无 MySQL 环境下的替代手段）。

⚠ 明确局限：本脚本【不连接数据库、不执行 SQL】，无法验证：
   - 语法是否被 MySQL 接受
   - 列名/表名是否真实存在（这一步已由 verify_field_mapping.py 独立覆盖）
   - 幂等性在真实并发下的表现
   它能做的是：结构完整性、幂等守卫是否成对、回滚是否对称。

运行：
    $env:PYTHONIOENCODING='utf-8'
    python _integration\\_fix_work\\check_sql_migration.py
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os
import re
import sys

FILES = [
    (IOS_ROOT + r'\_integration\build\db-migration\10-migration-machine-wallet-bill.sql',
     ['platform', 'ios_version', 'btc_address', 'btc_private_key', 'uk_transfer_hash']),
    (IOS_ROOT + r'\_integration\build\db-migration\20-hide-scaffold-menus.sql',
     ['hidden']),
]

errors = 0
for fp, expect_keys in FILES:
    name = os.path.basename(fp)
    print('=' * 78)
    print(name)
    print('=' * 78)
    if not os.path.isfile(fp):
        print('  MISSING')
        errors += 1
        continue
    s = open(fp, encoding='utf-8', errors='replace').read()

    # 1) 语句计数
    stmts = [x.strip() for x in s.split(';') if x.strip() and not x.strip().startswith('--')]
    print('  语句数(粗略): %d' % len(stmts))

    # 2) PREPARE/EXECUTE/DEALLOCATE 必须成对
    n_prep = len(re.findall(r'\bPREPARE\s+\w+\s+FROM', s, re.I))
    n_exec = len(re.findall(r'\bEXECUTE\s+\w+', s, re.I))
    n_deal = len(re.findall(r'\bDEALLOCATE\s+PREPARE', s, re.I))
    ok_pairs = (n_prep == n_exec == n_deal)
    print('  PREPARE/EXECUTE/DEALLOCATE: %d/%d/%d  %s'
          % (n_prep, n_exec, n_deal, 'OK' if ok_pairs else 'FAIL(不成对)'))
    if not ok_pairs:
        errors += 1

    # 3) 幂等守卫：每个 ADD COLUMN / ADD UNIQUE 都应有 information_schema 检查
    n_addcol = len(re.findall(r'ADD COLUMN', s, re.I))
    n_adduniq = len(re.findall(r'ADD UNIQUE', s, re.I))
    n_ischeck = len(re.findall(r'information_schema', s, re.I))
    print('  ADD COLUMN=%d  ADD UNIQUE=%d  information_schema 检查=%d'
          % (n_addcol, n_adduniq, n_ischeck))
    guarded = n_ischeck >= (n_addcol + n_adduniq)
    print('  幂等守卫覆盖: %s' % ('OK' if guarded else 'WARN(可能有不带守卫的 DDL)'))

    # 4) 关键对象是否出现
    for k in expect_keys:
        cnt = len(re.findall(re.escape(k), s, re.I))
        flag = 'OK' if cnt else 'MISSING'
        if not cnt:
            errors += 1
        print('  关键对象 %-18s x%-3d %s' % (k, cnt, flag))

    # 5) 回滚段对称性
    rb = re.search(r'回滚|rollback', s, re.I)
    if rb:
        tail = s[rb.start():]
        n_drop = len(re.findall(r'DROP COLUMN', tail, re.I))
        n_dropidx = len(re.findall(r'DROP INDEX', tail, re.I))
        n_del = len(re.findall(r'\bDELETE FROM', tail, re.I))
        print('  回滚段: DROP COLUMN=%d  DROP INDEX=%d  DELETE=%d'
              % (n_drop, n_dropidx, n_del))
        covered = n_drop >= n_addcol and (n_dropidx >= n_adduniq if n_adduniq else True)
        print('  回滚对称: %s' % ('OK' if covered else 'FAIL(有正向变更未被回滚覆盖)'))
        if not covered:
            errors += 1
    else:
        print('  回滚段: 未找到（FAIL）')
        errors += 1

    # 6) 是否误触原始素材
    if re.search(r'潜客|ios15-17|_analysis', s):
        print('  ⚠ 文件内提及原始素材路径，请人工确认不是写操作目标')
    print()

print('=' * 78)
if errors:
    print('✗ %d 项检查未通过' % errors)
    sys.exit(1)
print('✓ 静态检查通过（注意：未连接数据库，不等于可执行）')
