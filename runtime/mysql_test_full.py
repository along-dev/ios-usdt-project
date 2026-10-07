"""
MySQL/MariaDB 迁移验证：导入 schema → 执行迁移 → 验证幂等 → 验证回滚。
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os
import subprocess
import sys

BASE = IOS_ROOT + r'\_integration\_fix_work\_toolchain\mariadb-11.4.4-winx64\bin'
CLI = os.path.join(BASE, 'mariadb.exe')
SCHEMA = IOS_ROOT + r'\_integration\_build_ws_schema\qianke_schema.sql'
MIG = IOS_ROOT + r'\_integration\build\db-migration\10-migration-machine-wallet-bill.sql'
MENU = IOS_ROOT + r'\_integration\build\db-migration\20-hide-scaffold-menus.sql'
PORT = '13306'
DB = 'qk_test'

results = []


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


def step(title, rc, out, err, limit=30):
    print('--- %s (exit=%d) ---' % (title, rc))
    if out:
        for l in out.split('\n')[:limit]:
            print('   ', l)
    # 过滤常见无害告警
    real_err = [l for l in (err or '').split('\n')
                if l.strip() and 'ssl-verify-server-cert' not in l]
    if real_err:
        for l in real_err[:15]:
            print('  !', l)
    print()
    results.append((title, rc))
    return rc


print('=' * 78)
print('步骤 1：重建测试库')
print('=' * 78)
rc, o, e = cli("DROP DATABASE IF EXISTS %s; CREATE DATABASE %s DEFAULT CHARACTER SET utf8mb4;" % (DB, DB))
step('建库', rc, o, e)
if rc != 0:
    sys.exit(1)

print('=' * 78)
print('步骤 2：导入脱敏 schema')
print('=' * 78)
rc, o, e = cli(file=SCHEMA, db=DB)
step('导入 schema', rc, o, e)
if rc != 0:
    sys.exit(1)

rc, o, e = cli("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='%s';" % DB, db=DB)
step('导入后表数（期望 27）', rc, o, e)

print('=' * 78)
print('步骤 3：迁移前基线 —— 确认目标列不存在')
print('=' * 78)
pre = """SELECT 'machine.platform' AS col, COUNT(*) AS exists_flag FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA='%s' AND TABLE_NAME='machine' AND COLUMN_NAME='platform'
UNION ALL SELECT 'machine.ios_version', COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA='%s' AND TABLE_NAME='machine' AND COLUMN_NAME='ios_version'
UNION ALL SELECT 'wallet.btc_address', COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA='%s' AND TABLE_NAME='wallet' AND COLUMN_NAME='btc_address'
UNION ALL SELECT 'wallet.btc_private_key', COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA='%s' AND TABLE_NAME='wallet' AND COLUMN_NAME='btc_private_key'
UNION ALL SELECT 'bill.uk_transfer_hash', COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA='%s' AND TABLE_NAME='bill' AND INDEX_NAME='uk_transfer_hash';""" % (DB, DB, DB, DB, DB)
rc, o, e = cli(pre, db=DB)
step('迁移前（全部应为 0）', rc, o, e)

print('=' * 78)
print('步骤 4：执行迁移脚本 10-*.sql（第 1 次）')
print('=' * 78)
rc, o, e = cli(file=MIG, db=DB)
step('迁移第 1 次', rc, o, e)
if rc != 0:
    print('迁移失败，终止')
    sys.exit(1)

print('=' * 78)
print('步骤 5：执行迁移脚本（第 2 次，验证幂等）')
print('=' * 78)
rc, o, e = cli(file=MIG, db=DB)
step('迁移第 2 次（幂等）', rc, o, e)

print('=' * 78)
print('步骤 6：验证迁移结果')
print('=' * 78)
post = """SELECT 'machine.platform' AS col, COUNT(*) AS n FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA='%s' AND TABLE_NAME='machine' AND COLUMN_NAME='platform'
UNION ALL SELECT 'machine.ios_version', COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA='%s' AND TABLE_NAME='machine' AND COLUMN_NAME='ios_version'
UNION ALL SELECT 'wallet.btc_address', COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA='%s' AND TABLE_NAME='wallet' AND COLUMN_NAME='btc_address'
UNION ALL SELECT 'wallet.btc_private_key', COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA='%s' AND TABLE_NAME='wallet' AND COLUMN_NAME='btc_private_key'
UNION ALL SELECT 'bill.uk_transfer_hash', COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA='%s' AND TABLE_NAME='bill' AND INDEX_NAME='uk_transfer_hash';""" % (DB, DB, DB, DB, DB)
rc, o, e = cli(post, db=DB)
step('迁移后（全部应为 1）', rc, o, e)

rc, o, e = cli("SELECT d.id, d.type, dd.value FROM sys_dictionaries d "
               "LEFT JOIN sys_dictionary_details dd ON dd.sys_dictionary_id=d.id "
               "WHERE d.type='collect_mode';", db=DB)
step('collect_mode 字典', rc, o, e)

print('=' * 78)
print('步骤 7：隐藏脚手架菜单脚本')
print('=' * 78)
rc, o, e = cli(file=MENU, db=DB)
step('隐藏菜单', rc, o, e)

print('=' * 78)
print('步骤 8：回滚迁移')
print('=' * 78)
rollback = """
ALTER TABLE `machine` DROP COLUMN `platform`;
ALTER TABLE `machine` DROP COLUMN `ios_version`;
ALTER TABLE `wallet`  DROP COLUMN `btc_address`;
ALTER TABLE `wallet`  DROP COLUMN `btc_private_key`;
ALTER TABLE `bill`    DROP INDEX `uk_transfer_hash`;
DELETE dd FROM `sys_dictionary_details` dd
  JOIN `sys_dictionaries` d ON dd.`sys_dictionary_id` = d.`id`
  WHERE d.`type` = 'collect_mode';
DELETE FROM `sys_dictionaries` WHERE `type` = 'collect_mode';
"""
rc, o, e = cli(rollback, db=DB)
step('回滚', rc, o, e)

rc, o, e = cli(post, db=DB)
step('回滚后（应全部为 0）', rc, o, e)

print('=' * 78)
print('汇总')
print('=' * 78)
bad = [t for t, rc in results if rc != 0]
for t, rc in results:
    print('  %s %s' % ('OK  ' if rc == 0 else 'FAIL', t))
print()
if bad:
    print('✗ %d 步失败' % len(bad))
    sys.exit(1)
print('✓ 全部步骤通过')
