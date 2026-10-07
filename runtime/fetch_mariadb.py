"""
下载 MariaDB 便携版（zip），用 Python 绕过 schannel。

MariaDB 与 MySQL 在本次所需的 DDL 语法上兼容：
  information_schema、ALTER TABLE ADD COLUMN、UNIQUE KEY、
  PREPARE/EXECUTE/DEALLOCATE 全部支持。
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os
import sys
import ssl
import urllib.request

DEST = IOS_ROOT + r'\_integration\_fix_work\_toolchain'
os.makedirs(DEST, exist_ok=True)

# MariaDB 官方 Windows zip 镜像（stable）
VER = '11.4.4'
PKG = 'mariadb-%s-winx64.zip' % VER

CANDIDATES = [
    'https://mirror.nju.edu.cn/mariadb//mariadb-%s/winx64-packages/%s' % (VER, PKG),
    'https://mirrors.tuna.tsinghua.edu.cn/mariadb//mariadb-%s/winx64-packages/%s' % (VER, PKG),
    'https://archive.mariadb.org/mariadb-%s/winx64-packages/%s' % (VER, PKG),
    'https://mirrors.aliyun.com/mariadb//mariadb-%s/winx64-packages/%s' % (VER, PKG),
    'https://downloads.mariadb.org/rest-api/mariadb/%s/%s' % (VER, PKG),
]

out = os.path.join(DEST, PKG)
if os.path.isfile(out) and os.path.getsize(out) > 20_000_000:
    print('已存在: %s (%d bytes)' % (out, os.path.getsize(out)))
    sys.exit(0)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

for url in CANDIDATES:
    print('尝试: %s' % url)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=90, context=ctx) as r:
            final = r.geturl()
            total = int(r.headers.get('Content-Length') or 0)
            print('  HTTP %s -> %s (len=%s)' % (r.status, final[:90], total or '?'))
            got = 0
            with open(out, 'wb') as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
                    got += len(chunk)
        sz = os.path.getsize(out)
        print('  完成: %d bytes' % sz)
        if sz > 20_000_000:
            print('OK: %s' % out)
            sys.exit(0)
        print('  过小，试下一个')
    except Exception as e:
        print('  失败: %s' % str(e)[:130])

print('全部失败')
sys.exit(1)
