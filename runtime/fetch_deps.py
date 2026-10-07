"""下载 Redis + MongoDB 便携版（Windows），用 Python 绕过 schannel。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os
import ssl
import sys
import urllib.request

DEST = IOS_ROOT + r'\_integration\_fix_work\_toolchain'
os.makedirs(DEST, exist_ok=True)

TARGETS = [
    # (名称, [候选 URL...], 最小合法大小)
    ('redis', [
        'https://github.com/tporadowski/redis/releases/download/v5.0.14.1/Redis-x64-5.0.14.1.zip',
        'https://github.com/microsoftarchive/redis/releases/download/win-3.0.504/Redis-x64-3.0.504.zip',
    ], 1_000_000),
    ('mongodb', [
        'https://fastdl.mongodb.org/windows/mongodb-windows-x86_64-6.0.14.zip',
        'https://fastdl.mongodb.org/windows/mongodb-windows-x86_64-5.0.14.zip',
    ], 50_000_000),
]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def fetch(name, urls, minsize):
    for url in urls:
        fn = os.path.join(DEST, url.rsplit('/', 1)[-1])
        if os.path.isfile(fn) and os.path.getsize(fn) > minsize:
            print('[%s] 已存在: %s (%d bytes)' % (name, fn, os.path.getsize(fn)))
            return fn
        print('[%s] 尝试: %s' % (name, url))
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=120, context=ctx) as r:
                total = int(r.headers.get('Content-Length') or 0)
                print('    HTTP %s len=%s' % (r.status, total or '?'))
                got = 0
                with open(fn, 'wb') as f:
                    while True:
                        c = r.read(1 << 20)
                        if not c:
                            break
                        f.write(c)
                        got += len(c)
            sz = os.path.getsize(fn)
            print('    完成 %d bytes' % sz)
            if sz > minsize:
                return fn
            print('    过小，试下一个')
        except Exception as e:
            print('    失败: %s' % str(e)[:120])
    return None


ok = True
for name, urls, minsize in TARGETS:
    r = fetch(name, urls, minsize)
    if not r:
        ok = False
        print('[%s] ✗ 全部失败' % name)

print()
print('结果: %s' % ('全部就绪' if ok else '有失败项'))
sys.exit(0 if ok else 1)
