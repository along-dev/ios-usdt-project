"""
§4.2.5 最终验证（纯净库）：
  建库 → 导入真实菜单 → 基线(11 可见) → 执行隐藏 → 验证(0 可见)
  → 业务菜单未受影响 → 幂等 → 备份表回滚 → 还原一致
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
DB = 'qk_menu_v2'

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


def check(title, cond, detail=''):
    print('[%s] %s %s' % ('OK  ' if cond else 'FAIL', title, detail))
    RS.append((title, cond))


def show_out(label, o):
    if o:
        for l in o.split('\n')[:20]:
            print('        ', l)


# 生成纯菜单 SQL
if not os.path.isfile(TMP):
    s = open(SRC, encoding='utf-8', errors='replace').read()
    m = re.search(r'(CREATE TABLE `sys_base_menus`.*?;\s*)', s, re.S)
    ins = re.findall(r'(INSERT INTO `sys_base_menus`[^;]*;)', s)
    with open(TMP, 'w', encoding='utf-8', newline='') as f:
        f.write('DROP TABLE IF EXISTS `sys_base_menus`;\n' + m.group(1) + '\n')
        for x in ins:
            f.write(x + '\n')
    print('生成菜单 SQL: %d 条 INSERT' % len(ins))

VISIBLE_SQL = """SELECT
  SUM(CASE WHEN hidden=1 THEN 1 ELSE 0 END) AS hidden_n,
  SUM(CASE WHEN hidden=0 OR hidden IS NULL THEN 1 ELSE 0 END) AS visible_n
FROM sys_base_menus
WHERE name IN ('about','example','systemTools')
   OR component LIKE 'view/example/%'
   OR component LIKE 'view/systemTools/%';"""

print('=' * 78)
print('§4.2.5 最终验证（纯净库 qk_menu_v2）')
print('=' * 78)
print()

rc, o, e = cli("DROP DATABASE IF EXISTS %s; CREATE DATABASE %s DEFAULT CHARACTER SET utf8mb4;" % (DB, DB))
check('1. 建库', rc == 0)

rc, o, e = cli(file=TMP, db=DB)
check('2. 导入真实菜单数据', rc == 0)

rc, o, e = cli("SELECT COUNT(*) AS t FROM sys_base_menus;", db=DB)
check('3. 菜单总数=48', '48' in o, o.replace('\n', ' '))

rc, o, e = cli(VISIBLE_SQL, db=DB)
show_out('基线', o)
check('4. 基线：可见脚手架项=11（证明脚本确有必要）', '11' in o, o.replace('\n', ' '))

# 执行隐藏脚本
rc, o, e = cli(file=MENU, db=DB)
real_err = [l for l in (e or '').split('\n') if l.strip() and 'ssl-verify' not in l]
check('5. 执行隐藏脚本', rc == 0 and not real_err, ('ERR: ' + str(real_err[:3])) if real_err else '')

rc, o, e = cli(VISIBLE_SQL, db=DB)
show_out('隐藏后', o)
check('6. 隐藏后：可见脚手架项=0', '0' in o.split('\n')[-1], o.replace('\n', ' '))

rc, o, e = cli("SELECT COUNT(*) AS c FROM sys_base_menus WHERE id>=28 AND (hidden=0 OR hidden IS NULL);", db=DB)
check('7. 业务菜单未受影响（21 条仍可见）', '21' in o, o.replace('\n', ' '))

rc, o, e = cli(file=MENU, db=DB)
check('8. 幂等：第 2 次执行', rc == 0)
rc, o, e = cli(VISIBLE_SQL, db=DB)
check('9. 幂等后仍为 0', '0' in o.split('\n')[-1], o.replace('\n', ' '))

rc, o, e = cli("SELECT COUNT(*) AS c FROM `_bak_sys_base_menus_hidden`;", db=DB)
check('10. 备份表存在且 48 行', '48' in o, o.replace('\n', ' '))

# 备份表回滚
rc, o, e = cli("""UPDATE `sys_base_menus` m
  JOIN `_bak_sys_base_menus_hidden` b ON b.`id` = m.`id`
   SET m.`hidden` = b.`hidden`;""", db=DB)
check('11. 备份表回滚', rc == 0 and not [l for l in (e or '').split('\n') if l.strip() and 'ssl-verify' not in l])

rc, o, e = cli(VISIBLE_SQL, db=DB)
show_out('回滚后', o)
check('12. 回滚后恢复 11 可见（与基线一致）', '11' in o, o.replace('\n', ' '))

# 回滚精确性：dashboard/person/autoCodeEdit 应保持 hidden=1
rc, o, e = cli("SELECT id, name, hidden FROM sys_base_menus WHERE id IN (1,8,25) ORDER BY id;", db=DB)
show_out('原本就隐藏的项', o)
ok = all(('\t1' in l) for l in o.split('\n')[1:] if l.strip())
check('13. 回滚未误改原本隐藏项（1/8/25 仍 hidden=1）', ok)

print()
print('=' * 78)
bad = [t for t, ok in RS if not ok]
for t, ok in RS:
    print('  %s %s' % ('OK  ' if ok else 'FAIL', t))
print()
if bad:
    print('✗ %d 项未通过' % len(bad))
    sys.exit(1)
print('✓ 全部通过（%d 项）' % len(RS))
