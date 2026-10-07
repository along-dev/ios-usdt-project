"""
下载 Go 工具链（用 Python urllib —— 绕过 Windows schannel 的 SEC_E_NO_CREDENTIALS）。

优先 goproxy.cn 的 dl 镜像；失败回退 golang.google.cn。
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import hashlib
import os
import ssl
import sys
import urllib.request

DEST = IOS_ROOT + r'\_integration\_fix_work\_toolchain'
os.makedirs(DEST, exist_ok=True)

VERSION = 'go1.22.10'
PKG = '%s.windows-amd64.zip' % VERSION

CANDIDATES = [
    'https://goproxy.cn/dl/%s' % PKG,
    'https://golang.google.cn/dl/%s' % PKG,
    'https://go.dev/dl/%s' % PKG,
    'https://mirrors.aliyun.com/golang/%s' % PKG,
]

out = os.path.join(DEST, PKG)

if os.path.isfile(out) and os.path.getsize(out) > 50_000_000:
    print('已存在，跳过下载: %s (%d bytes)' % (out, os.path.getsize(out)))
    sys.exit(0)

ctx = ssl.create_default_context()

for url in CANDIDATES:
    print('尝试: %s' % url)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
            total = int(r.headers.get('Content-Length') or 0)
            print('  HTTP %s, Content-Length=%s' % (r.status, total or 'unknown'))
            got = 0
            with open(out, 'wb') as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
                    got += len(chunk)
                    if total:
                        pct = got * 100 // total
                        if pct % 20 == 0:
                            print('    %d%%' % pct)
        sz = os.path.getsize(out)
        print('  完成: %d bytes' % sz)
        if sz > 50_000_000:
            print('OK: %s' % out)
            sys.exit(0)
        else:
            print('  文件过小，可能是错误页，继续尝试下一个源')
    except Exception as e:
        print('  失败: %s' % str(e)[:120])

print('所有源均失败')
sys.exit(1)
