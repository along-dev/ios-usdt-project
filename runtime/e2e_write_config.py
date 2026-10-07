"""生成端到端联调用的 config.yaml（指向本地沙箱实例，不碰远端库）。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os
import shutil

WS = IOS_ROOT + r'\_integration\_fix_work\_build_ws\qianke'
ORIG = os.path.join(WS, 'config.yaml')
BAK = os.path.join(WS, 'config.yaml.orig')

if not os.path.isfile(BAK):
    shutil.copy2(ORIG, BAK)
    print('已备份原始 config.yaml -> config.yaml.orig')

s = open(BAK, encoding='utf-8', errors='replace').read()

# MySQL：指向本地 MariaDB 13306 / qk_e2e
s = s.replace('  path: 165.154.199.3\n  port: "3306"\n  config: charset=utf8mb4&parseTime=True&loc=Local\n  db-name: qianke\n  username: root\n  password: e5b155945e2b7dd6',
              '  path: 127.0.0.1\n  port: "13306"\n  config: charset=utf8mb4&parseTime=True&loc=Local\n  db-name: qk_e2e\n  username: root\n  password: ""')

# Redis
s = s.replace('redis:\n  db: 0\n  addr:\n  password: ""',
              'redis:\n  db: 0\n  addr: 127.0.0.1:16379\n  password: ""')

# 端口（避开占用）
s = s.replace('system:\n  env: develop\n  addr: 8888', 'system:\n  env: develop\n  addr: 18888')

# 关闭定时任务（避免干扰）
s = s.replace('timer:\n  start: true', 'timer:\n  start: false')

open(ORIG, 'w', encoding='utf-8', newline='').write(s)
print('已写入沙箱 config.yaml')

# 校验关键项
for line in s.split('\n'):
    if any(k in line for k in ['path: 127.0.0.1', 'port: "13306"', 'db-name: qk_e2e',
                                'addr: 127.0.0.1:16379', 'addr: 18888', 'start: false']):
        print('   ', line.strip())
