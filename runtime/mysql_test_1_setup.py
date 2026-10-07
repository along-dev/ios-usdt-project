"""
建库 + 导入 schema + 执行迁移脚本 + 验证幂等/回滚。
用 Python 的 subprocess 驱动 mariadb.exe 客户端。
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
DATA = IOS_ROOT + r'\_integration\_fix_work\_mysqldata'
SCHEMA = IOS_ROOT + r'\_integration\_build_ws_schema\qianke_schema.sql'
MIG = IOS_ROOT + r'\_integration\build\db-migration\10-migration-machine-wallet-bill.sql'
MENU = IOS_ROOT + r'\_integration\build\db-migration\20-hide-scaffold-menus.sql'

PORT = '13306'


def run_cli(sql=None, file=None, db=None, user='root'):
    cmd = [CLI, '-h', '127.0.0.1', '-P', PORT, '-u', user,
           '--protocol=TCP', '--default-character-set=utf8mb4']
    if db:
        cmd.append(db)
    if file:
        cmd += ['-e', 'source ' + file.replace('\\', '/')]
    elif sql:
        cmd += ['-e', sql]
    p = subprocess.run(cmd, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return p.returncode, p.stdout, p.stderr


def show(title, rc, out, err):
    print('--- %s (exit=%d) ---' % (title, rc))
    if out.strip():
        for l in out.strip().split('\n')[:25]:
            print('   ', l)
    if err.strip():
        for l in err.strip().split('\n')[:15]:
            print('  !', l)
    print()
    return rc


print('=' * 78)
print('步骤 1：建库')
print('=' * 78)
rc, o, e = run_cli("DROP DATABASE IF EXISTS qk_test; CREATE DATABASE qk_test DEFAULT CHARACTER SET utf8mb4;")
show('create database', rc, o, e)
if rc != 0:
    sys.exit(1)

print('=' * 78)
print('步骤 2：导入 schema（脱敏后的 qianke.sql，无 INSERT）')
print('=' * 78)
if not os.path.isfile(SCHEMA):
    print('  schema 不存在:', SCHEMA)
    print('  先运行 build_unified.ps1 生成产物，或指定其它路径')
    sys.exit(2)
rc, o, e = run_cli(file=SCHEMA, db='qk_test')
show('import schema', rc, o, e)
if rc != 0:
    sys.exit(1)

rc, o, e = run_cli("SELECT COUNT(*) AS tables_count FROM information_schema.TABLES WHERE TABLE_SCHEMA='qk_test';", db='qk_test')
show('导入后表数', rc, o, e)
