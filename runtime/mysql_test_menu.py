"""
单独验证 20-hide-scaffold-menus.sql：
脱敏 schema 里 sys_base_menus 是空表（INSERT 被删），
故需先从原始 dump 中提取菜单数据单独导入，才能真实测试隐藏逻辑。
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
SRC = QIANKE_SRC + r'\qianke\qianke0301.sql'
MENU = IOS_ROOT + r'\_integration\build\db-migration\20-hide-scaffold-menus.sql'
TMP = IOS_ROOT + r'\_integration\_fix_work\_menus_only.sql'
PORT = '13306'
DB = 'qk_menu_test'


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


def show(t, rc, out, err):
    print('--- %s (exit=%d) ---' % (t, rc))
    if out:
        for l in out.split('\n')[:40]:
            print('   ', l)
    real = [l for l in (err or '').split('\n')
            if l.strip() and 'ssl-verify-server-cert' not in l]
    if real:
        for l in real[:12]:
            print('  !', l)
    print()
    return rc


# 1) 从原始 dump 抽取 sys_base_menus 的 DDL + INSERT
print('=' * 78)
print('步骤 1：从原始 dump 抽取 sys_base_menus 数据')
print('=' * 78)
s = open(SRC, encoding='utf-8', errors='replace').read()
m = re.search(r'(CREATE TABLE `sys_base_menus`.*?;\s*)', s, re.S)
ddl = m.group(1) if m else ''
ins = re.findall(r'(INSERT INTO `sys_base_menus`[^;]*;)', s)
print('  DDL: %d 字节' % len(ddl))
print('  INSERT: %d 条' % len(ins))
if not ddl or not ins:
    print('  抽取失败')
    sys.exit(1)

with open(TMP, 'w', encoding='utf-8', newline='') as f:
    f.write('DROP TABLE IF EXISTS `sys_base_menus`;\n')
    f.write(ddl)
    f.write('\n')
    for x in ins:
        f.write(x + '\n')
print('  写入临时文件: %s' % TMP)

# 2) 建库 + 导入菜单
print()
print('=' * 78)
print('步骤 2：建库并导入菜单数据')
print('=' * 78)
rc, o, e = cli("DROP DATABASE IF EXISTS %s; CREATE DATABASE %s DEFAULT CHARACTER SET utf8mb4;" % (DB, DB))
show('建库', rc, o, e)
rc, o, e = cli(file=TMP, db=DB)
show('导入菜单', rc, o, e)

rc, o, e = cli("SELECT COUNT(*) AS total FROM sys_base_menus;", db=DB)
show('菜单总数', rc, o, e)

# 3) 隐藏前基线：脚手架项可见数量
PRE = """SELECT COUNT(*) AS visible_scaffold FROM sys_base_menus
 WHERE (name IN ('about','example','systemTools')
     OR component LIKE 'view/example/%%'
     OR component LIKE 'view/systemTools/%%')
   AND (hidden = 0 OR hidden IS NULL);"""
rc, o, e = cli(PRE, db=DB)
show('隐藏前：可见脚手架项（应 >0）', rc, o, e)

# 4) 执行隐藏脚本
print()
print('=' * 78)
print('步骤 3：执行 20-hide-scaffold-menus.sql')
print('=' * 78)
rc, o, e = cli(file=MENU, db=DB)
show('隐藏菜单', rc, o, e)

# 5) 隐藏后验证
rc, o, e = cli(PRE, db=DB)
show('隐藏后：可见脚手架项（应为 0）', rc, o, e)

# 6) 业务菜单未受影响
rc, o, e = cli("""SELECT id, name, title, hidden FROM sys_base_menus
 WHERE id >= 28 AND menu_level = 0 ORDER BY id LIMIT 12;""", db=DB)
show('业务菜单（应仍 visible）', rc, o, e)

# 7) 幂等：再执行一次
print()
print('=' * 78)
print('步骤 4：幂等复跑')
print('=' * 78)
rc, o, e = cli(file=MENU, db=DB)
show('隐藏菜单（第 2 次）', rc, o, e)
rc, o, e = cli(PRE, db=DB)
show('第 2 次后可见脚手架项（仍应为 0）', rc, o, e)
