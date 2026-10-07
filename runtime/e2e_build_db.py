"""端到端联调：建业务库（schema + 迁移 + 种子数据 + getAppJWT 需要的表）"""
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
SEED = IOS_ROOT + r'\_integration\_fix_work\e2e_seed.sql'
PORT = '13306'
DB = 'qk_e2e'


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


def run(title, sql=None, file=None, db=None):
    rc, o, e = cli(sql, file, db)
    real = [l for l in (e or '').split('\n') if l.strip() and 'ssl-verify' not in l]
    print('[%s] %s' % ('OK  ' if rc == 0 and not real else 'FAIL', title))
    if o:
        for l in o.split('\n')[:14]:
            print('       ', l)
    if real:
        for l in real[:10]:
            print('     !', l)
    return rc, o, e


print('=' * 78)
print('构建端到端业务库 %s' % DB)
print('=' * 78)
run('1. 重建库', "DROP DATABASE IF EXISTS %s; CREATE DATABASE %s DEFAULT CHARACTER SET utf8mb4;" % (DB, DB))
run('2. 导入 schema', file=SCHEMA, db=DB)
run('3. 执行迁移', file=MIG, db=DB)
run('4. 导入种子数据', file=SEED, db=DB)

print()
print('=' * 78)
print('关键数据确认')
print('=' * 78)
run('machine', "SELECT id,device_id,agent_id,platform,ios_version FROM machine;", db=DB)
run('wallet', "SELECT id,wallet_name,type,region,progress,btc_address FROM wallet;", db=DB)
run('链路 machine->agent->packet',
    "SELECT m.id mid, a.id aid, a.ratio, p.id pid, p.technical_service_fee tsf "
    "FROM machine m LEFT JOIN agent a ON m.agent_id=a.id "
    "LEFT JOIN packet p ON a.packet_id=p.id WHERE m.id=1;", db=DB)
