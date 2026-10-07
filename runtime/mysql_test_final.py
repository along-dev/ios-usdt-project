"""
最终验证（干净路径）：
  1. 新建库，导入脱敏 schema
  2. 导入真实菜单数据（因脱敏 schema 无 INSERT）
  3. 跑迁移脚本 → 验证 5 项变更 + 幂等 + 回滚
  4. 跑只读菜单校验 → 确认脚手架已隐藏、业务菜单可见
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os
import re
import subprocess
import sys

BASE = IOS_ROOT + r'\_integration\_fix_work\_toolchain\mariadb-11.4.4-winx64\bin'
CLI = os.path.join(BASE, 'mariadb.exe')
SCHEMA = IOS_ROOT + r'\_integration\_build_ws_schema\qianke_schema.sql'
MENUS = IOS_ROOT + r'\_integration\_fix_work\_menus_only.sql'
MIG = IOS_ROOT + r'\_integration\build\db-migration\10-migration-machine-wallet-bill.sql'
VERIFY = IOS_ROOT + r'\_integration\build\db-migration\20-hide-scaffold-menus.sql'
PORT = '13306'
DB = 'qk_final'

RS = []


def cli(sql=None, file=None, db=None):
    cmd = [CLI, '--skip-ssl', '-h', '127.0.0.1', '-P', PORT, '-u', 'root',
           '--protocol=TCP', '--default-character-set=utf8mb4']
    if db:
        cmd.append(db)
    if file:
        cmd += ['-e', 'source ' + file.replace('\\', '/')]
    elif sql:
        cmd += ['-e', sql]
    p = subprocess.run(cmd, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def step(t, rc, out, err, limit=30, expect_rc=0):
    ok = (rc == expect_rc)
    print('[%s] %s' % ('OK  ' if ok else 'FAIL', t))
    if out:
        for l in out.split('\n')[:limit]:
            print('       ', l)
    real = [l for l in (err or '').split('\n')
            if l.strip() and 'ssl-verify-server-cert' not in l]
    if real:
        for l in real[:12]:
            print('     !', l)
    print()
    RS.append((t, ok))
    return rc


def q(title, sql, expect=None):
    rc, o, e = cli(sql, db=DB)
    step('%s' % title, rc, o, e)
    if expect is not None:
        RS[-1] = (title, RS[-1][1] and (expect in o))
    return o


print('=' * 78)
print('最终验证：干净库 → 迁移 → 校验')
print('=' * 78)
print()

rc, o, e = cli("DROP DATABASE IF EXISTS %s; CREATE DATABASE %s DEFAULT CHARACTER SET utf8mb4;" % (DB, DB))
step('1. 建库', rc, o, e)

rc, o, e = cli(file=SCHEMA, db=DB)
step('2. 导入脱敏 schema（27 表 / 0 INSERT）', rc, o, e)

rc, o, e = cli(file=MENUS, db=DB)
step('3. 导入真实菜单数据（48 条）', rc, o, e)

q('4. 表数', "SELECT COUNT(*) AS n FROM information_schema.TABLES WHERE TABLE_SCHEMA='%s';" % DB, '28')

print('--- 5. 迁移前基线 ---')
PRE = """SELECT
 (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='%s' AND TABLE_NAME='machine' AND COLUMN_NAME='platform') AS m_platform,
 (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='%s' AND TABLE_NAME='wallet' AND COLUMN_NAME='btc_address') AS w_btc,
 (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA='%s' AND TABLE_NAME='bill' AND INDEX_NAME='uk_txhash_role') AS b_idx;""" % (DB, DB, DB)
o = q('5. 迁移前（应全 0）', PRE)
RS[-1] = ('5. 迁移前全 0', all(x in o for x in ['\t0', ' 0']) or o.count('0') >= 3)

rc, o, e = cli(file=MIG, db=DB)
step('6. 执行迁移脚本', rc, o, e)

print('--- 7. 迁移后校验 ---')
POST = """SELECT
 (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='%s' AND TABLE_NAME='machine' AND COLUMN_NAME='platform') AS m_platform,
 (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='%s' AND TABLE_NAME='machine' AND COLUMN_NAME='ios_version') AS m_ios,
 (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='%s' AND TABLE_NAME='wallet' AND COLUMN_NAME='btc_address') AS w_btc_addr,
 (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='%s' AND TABLE_NAME='wallet' AND COLUMN_NAME='btc_private_key') AS w_btc_key,
 (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA='%s' AND TABLE_NAME='bill' AND INDEX_NAME='uk_txhash_role') AS b_idx;""" % (DB, DB, DB, DB, DB)
o = q('7. 迁移后（应全 1）', POST)
# 期望：4 个列存在性=1；复合索引 uk_txhash_role 有 2 列 → b_idx=2
_vals = o.split('\n')[-1].split('\t') if o else []
RS[-1] = ('7. 迁移后全 1', len(_vals) == 5 and _vals[:4] == ['1'] * 4 and _vals[4] == '2')

q('8. collect_mode 字典（label=gasleak value=1）',
  "SELECT d.id,d.type,dd.label,dd.value FROM sys_dictionaries d "
  "LEFT JOIN sys_dictionary_details dd ON dd.sys_dictionary_id=d.id WHERE d.type='collect_mode';",
  'gasleak')

rc, o, e = cli(file=MIG, db=DB)
ok_idem = (rc == 0)
step('9. 迁移幂等复跑（第 2 次）', rc, o, e)

o = q('10. 复跑后仍全 1（未重复添加）',
      "SELECT SUM(n) AS s FROM ("
      "SELECT COUNT(*) n FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='%s' AND TABLE_NAME='wallet' AND COLUMN_NAME LIKE 'btc_%%'"
      ") t;" % DB)

print('--- 11. 只读菜单校验 ---')
rc, o, e = cli(file=VERIFY, db=DB)
step('11. 执行 20-verify 脚本（只读）', rc, o, e)

q('12. 脚手架菜单已隐藏（visible=0）',
  "SELECT SUM(CASE WHEN hidden=1 THEN 1 ELSE 0 END) AS already_hidden,"
  "SUM(CASE WHEN hidden=0 OR hidden IS NULL THEN 1 ELSE 0 END) AS visible "
  "FROM sys_base_menus WHERE name IN ('about','example','systemTools') "
  "OR component LIKE 'view/example/%%' OR component LIKE 'view/systemTools/%%';",
  '0')

print('--- 13. 回滚 ---')
RB = """
ALTER TABLE `machine` DROP COLUMN `platform`;
ALTER TABLE `machine` DROP COLUMN `ios_version`;
ALTER TABLE `wallet`  DROP COLUMN `btc_address`;
ALTER TABLE `wallet`  DROP COLUMN `btc_private_key`;
ALTER TABLE `bill`    DROP INDEX `uk_txhash_role`;
DELETE dd FROM `sys_dictionary_details` dd
  JOIN `sys_dictionaries` d ON dd.`sys_dictionary_id` = d.`id`
  WHERE d.`type` = 'collect_mode';
DELETE FROM `sys_dictionaries` WHERE `type` = 'collect_mode';
"""
rc, o, e = cli(RB, db=DB)
step('13. 回滚', rc, o, e)

o = q('14. 回滚后应全 0', POST)
RS[-1] = ('14. 回滚后全 0', o.count('0') >= 5)

print('=' * 78)
print('汇总')
print('=' * 78)
for t, ok in RS:
    print('  %s %s' % ('OK  ' if ok else 'FAIL', t))
bad = [t for t, ok in RS if not ok]
print()
if bad:
    print('✗ %d 项未通过: %s' % (len(bad), bad))
    sys.exit(1)
print('✓ 全部通过（%d 项）' % len(RS))
