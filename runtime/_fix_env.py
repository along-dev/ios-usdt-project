# -*- coding: utf-8 -*-
"""重写 .env：把任何形式的中文路径前缀替换为 X:（用行级重写，不依赖正则匹配中文）。"""
p = IOS_ROOT + r"\_integration\_fix_work\_i1c3_ws\.env"

lines = [
    "PORT=3000",
    "MONGO_URI=mongodb://127.0.0.1:27018/gasleak",
    "REDIS_URL=redis://127.0.0.1:16379",
    r"STORAGE_ROOT=X:\_integration\_fix_work\_i1c3_storage",
    r"LOG_DIR=X:\_integration\_fix_work\_i1c3_logs",
    "LOG_RETAIN_DAYS=1",
    "JWT_SECRET=i1c3-e2e-jwt-secret",
    "DEFAULT_ADMIN_PASSWORD=i1c3-e2e-admin",
    "TOTP_REQUIRED=false",
    "WORKERS=1",
    "ADMIN_DOMAIN=localhost",
    "NODE_ENV=development",
    "QIANKE_API_BASE=http://127.0.0.1:8888",
    "QIANKE_SERVICE_TOKEN=i2c1-e2e-token",
]
data = ("\n".join(lines) + "\n").encode("utf-8")
with open(p, "wb") as f:
    f.write(data)

print("已重写，大小:", len(data))
print(open(p, encoding="utf-8").read())

import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")