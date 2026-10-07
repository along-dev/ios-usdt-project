"""测试网络可达性 —— 用 Python 自带的 OpenSSL，绕过 Windows schannel 问题。"""
import ssl
import sys
import urllib.request

urls = [
    'https://goproxy.cn',
    'https://mirrors.aliyun.com',
    'https://golang.google.cn',
    'https://go.dev',
]

print('Python SSL:', ssl.OPENSSL_VERSION)
print()

for u in urls:
    req = urllib.request.Request(u, method='HEAD')
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            print('  %-32s -> HTTP %s' % (u, r.status))
    except Exception as e:
        msg = str(e)
        print('  %-32s -> FAIL %s' % (u, msg[:80]))
