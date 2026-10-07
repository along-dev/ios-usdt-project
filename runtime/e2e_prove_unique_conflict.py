"""确认 uk_transfer_hash 与多行分账的根本冲突。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os
import subprocess

BASE = IOS_ROOT + r'\_integration\_fix_work\_toolchain\mariadb-11.4.4-winx64\bin'
CLI = os.path.join(BASE, 'mariadb.exe')
DB = 'qk_e2e'


def sql(q):
    cmd = [CLI, '--skip-ssl', '-h', '127.0.0.1', '-P', '13306', '-u', 'root',
           '--protocol=TCP', '--default-character-set=utf8mb4', DB, '-e', q]
    p = subprocess.run(cmd, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return p.stdout.strip(), p.stderr.strip()


print('=== 直接验证：同一 tx_hash 插 3 行（role 1/2/3）会被唯一索引拒绝 ===')
o, e = sql("""
INSERT INTO bill (wallet_id,token_id,role,batch_id,total_num,num,usdt_num,settlement_id,order_id,transfer_hash,create_time,status)
VALUES (1,1,1,1,'100','10','10',1,'o1','0xUNIQTEST','2026-09-26',1);
INSERT INTO bill (wallet_id,token_id,role,batch_id,total_num,num,usdt_num,settlement_id,order_id,transfer_hash,create_time,status)
VALUES (1,1,2,1,'100','70','70',3,'o2','0xUNIQTEST','2026-09-26',1);
""")
print('stdout:', o[:200])
print('stderr:', e[:300])
print()

o, e = sql("SELECT COUNT(*) AS n FROM bill WHERE transfer_hash='0xUNIQTEST';")
print('插入条数:', o.replace('\n', ' '))
print()

print('=== 结论 ===')
print('  uk_transfer_hash 是【全列唯一】，而分账需为同一 tx_hash 写多行（role 1/2/3）。')
print('  两者根本冲突 —— 第一次插入成功后，第二行必然 1062。')
print('  正确设计：唯一键应为 (transfer_hash, role) 复合。')
