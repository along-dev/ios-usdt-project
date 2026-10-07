"""查清脚手架菜单的真实 hidden 分布 —— 逐条打印，判定 4/11 与 15/0 哪个对。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os
import subprocess

BASE = IOS_ROOT + r'\_integration\_fix_work\_toolchain\mariadb-11.4.4-winx64\bin'
CLI = os.path.join(BASE, 'mariadb.exe')
PORT = '13306'


def cli(sql, db):
    cmd = [CLI, '--skip-ssl', '-h', '127.0.0.1', '-P', PORT, '-u', 'root',
           '--protocol=TCP', '--default-character-set=utf8mb4', db, '-e', sql]
    p = subprocess.run(cmd, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return p.returncode, p.stdout.strip(), p.stderr.strip()


SQL = """
SELECT id, menu_level, parent_id, name, component, hidden
  FROM sys_base_menus
 WHERE name IN ('about','example','systemTools')
    OR component LIKE 'view/example/%'
    OR component LIKE 'view/systemTools/%'
 ORDER BY id;
"""

for db in ['qk_final', 'qk_menu_test']:
    print('=' * 90)
    print('库:', db)
    print('=' * 90)
    rc, o, e = cli(SQL, db)
    print(o)
    if e and 'ssl-verify' not in e:
        print('ERR:', e[:200])
    print()
