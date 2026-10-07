# -*- coding: utf-8 -*-
"""从 Redis 取 gin-vue-admin 的验证码答案（captchaId -> code）。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import subprocess
import sys

REDIS = IOS_ROOT + r"\_integration\_fix_work\_toolchain\redis\redis-cli.exe"
HOST = "127.0.0.1"
PORT = "16379"


def cli(*args):
    r = subprocess.run([REDIS, "-h", HOST, "-p", PORT] + list(args),
                       capture_output=True, text=True, timeout=15)
    return r.stdout.strip(), r.stderr.strip()


print("=== 1) PING ===")
out, err = cli("PING")
print("  ", out or err)

print("")
print("=== 2) 全部 key ===")
out, err = cli("KEYS", "*")
keys = [k for k in out.splitlines() if k.strip()]
for k in keys[:40]:
    print("  ", k)
print("  总数:", len(keys))

print("")
print("=== 3) 找 captcha 相关 ===")
for k in keys:
    if "captcha" in k.lower():
        t, _ = cli("TYPE", k)
        v, _ = cli("GET", k) if t == "string" else ("(非string)", "")
        print("   %s  type=%s  value=%s" % (k, t, v))
