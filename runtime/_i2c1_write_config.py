# -*- coding: utf-8 -*-
"""
I2-C1：生成 e2e 用的 config.yaml（指向本地沙盒实例，不碰远端库）。
★ 只写 _fix_work/_i2c1_ws/ 下的副本，不改 01-backend-go 的 config。
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os

WS = IOS_ROOT + r"\_integration\_fix_work\_i2c1_ws"
ORIG = os.path.join(WS, "config.yaml.orig")
OUT = os.path.join(WS, "config.yaml")

s = open(ORIG, encoding="utf-8", errors="replace").read()

# MySQL -> 本地 MariaDB 13306 / qk_e2e
s = s.replace('  path: ${MYSQL_HOST}\n  port: "3306"', '  path: 127.0.0.1\n  port: "13306"')
s = s.replace("  db-name: qianke", "  db-name: qk_e2e")
s = s.replace("  password: ${MYSQL_PASSWORD}", '  password: ""')

# Redis -> 本地 16379
s = s.replace("redis:\n  db: 0\n  addr:\n  password: \"\"",
              "redis:\n  db: 0\n  addr: 127.0.0.1:16379\n  password: \"\"")

# Go 端口 -> 调度表规定的 8888
s = s.replace("system:\n  env: develop\n  addr: 8888",
              "system:\n  env: develop\n  addr: 8888")
# 使用 redis
s = s.replace("  use-redis: false", "  use-redis: true")

# 关闭定时任务（避免干扰 e2e）
s = s.replace("timer:\n  start: true", "timer:\n  start: false")

# ★ C-2：服务间密钥（e2e 用固定测试值，非生产凭据）
s = s.replace('  service-token: ""', '  service-token: "i2c1-e2e-token"')

# signing-key / jwt signing-key（占位符 -> e2e 测试值）
s = s.replace("signing-key: ${SIGNING_KEY}", 'signing-key: "i2c1-e2e-signing-key"')

open(OUT, "w", encoding="utf-8", newline="").write(s)
print("已写出:", OUT)

# 校验关键项
keys = ["path: 127.0.0.1", 'port: "13306"', "db-name: qk_e2e",
        "addr: 127.0.0.1:16379", "addr: 8888", "start: false",
        "i2c1-e2e-token", "use-redis: true"]
print("关键项校验:")
for line in s.split("\n"):
    for k in keys:
        if k in line:
            print("   ", line.strip())
            break
