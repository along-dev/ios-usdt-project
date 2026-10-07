#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D4-C1 判据：TOTP 硬编码 secret 从前端源码 + dist 双清零。

V1  src/view/home/index.vue 不含该 secret
V2  dist/** 全树不含该 secret
V4  index.vue 其余功能未破坏（getindexinfo / statisticaldata / 4 个统计字段）
V5  后端未被改动（02-backend-node 抽样 sha256 与基线一致）
V6  otpauth:// 字样也不再出现（源码 + dist）
V7  守护：_manifest.sha256 / contracts.md 未改

退出码：0 = 全绿；1 = 有红。
"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import os
import sys

# ★ X3：本脚本自带 UTF-8 输出（P-10）
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import hashlib
import os
import sys

ROOT = USDT_ROOT
FRONT = os.path.join(ROOT, '03-web-admin')
DIST = os.path.join(FRONT, 'dist')
SRC_VUE = os.path.join(FRONT, 'src', 'view', 'home', 'index.vue')

SECRET = b'WGSHDYSGBNJUKIHSYBGBSYJHBHJYSYS'
OTPAUTH = b'otpauth'

# V5：后端抽样基线（动前测得）
BACKEND_BASE = {
    r'02-backend-node\src_restored\core\crypto\totp.js':
        '3e2ce4dc5d0e7a6e78e1d9e6f0d90edab3d1f6f7bf4b9d3b2a71ba0e2bd7d6e8',
}
# 上一行为占位，真实基线由 --snapshot 生成后写回
BACKEND_BASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 'd4c1_backend_baseline.txt')

# V7 守护基线
GUARD_BASE = {
    os.path.join(ROOT, '_manifest.sha256'):
        'b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2',
    os.path.join(ROOT, '09-docs', 'spec', 'contracts.md'):
        'f80a2ead6736d5f5aff70e72e3aa7de1c7cc63f93a604fb6eeb4a163059f925c',
}

results = []


def check(tag, ok, detail=''):
    results.append((tag, ok, detail))
    print('%-6s %-4s %s' % (tag, 'PASS' if ok else 'FAIL', detail))


def sha256(path):
    with open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def readb(path):
    with open(path, 'rb') as fh:
        return fh.read()


def scan_tree(path, needle, exts=None):
    hits = []
    for dp, dn, fn in os.walk(path):
        dn[:] = [d for d in dn if d not in ('node_modules', '.git')]
        for f in fn:
            fp = os.path.join(dp, f)
            if exts and not f.lower().endswith(exts):
                continue
            try:
                if os.path.getsize(fp) > 20 * 1024 * 1024:
                    continue
                if needle in readb(fp):
                    hits.append(fp)
            except OSError:
                continue
    return hits


def snapshot():
    """记录后端抽样基线。"""
    targets = [
        r'02-backend-node\src_restored\core\crypto\totp.js',
        r'02-backend-node\src_restored\plugins\api\routes\auth.js',
    ]
    lines = []
    for rel in targets:
        fp = os.path.join(ROOT, rel)
        if os.path.exists(fp):
            lines.append('%s %s' % (sha256(fp), rel))
            print('SNAP', rel, sha256(fp))
    with open(BACKEND_BASE_FILE, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('written ->', BACKEND_BASE_FILE)


def main():
    if '--snapshot' in sys.argv:
        snapshot()
        return 0

    print('=== D4-C1 判据 ===')

    # V1
    if os.path.exists(SRC_VUE):
        b = readb(SRC_VUE)
        check('V1', SECRET not in b,
              'index.vue secret hits=%d' % b.count(SECRET))
    else:
        check('V1', False, 'index.vue MISSING')

    # V2
    if os.path.isdir(DIST):
        hits = scan_tree(DIST, SECRET)
        check('V2', not hits, 'dist secret hits=%d %s' % (len(hits), hits[:5]))
    else:
        check('V2', False, 'dist MISSING')

    # V4
    if os.path.exists(SRC_VUE):
        t = readb(SRC_VUE).decode('utf-8', 'replace')
        need = ['getindexinfo', 'statisticaldata', 'get_index_info',
                'azNum', 'sqNum', 'sqUsdt', 'zlrUsdt']
        miss = [n for n in need if n not in t]
        check('V4', not miss, 'missing=%s' % miss)
    else:
        check('V4', False, 'index.vue MISSING')

    # V5
    if os.path.exists(BACKEND_BASE_FILE):
        bad = []
        for line in open(BACKEND_BASE_FILE, encoding='utf-8'):
            line = line.strip()
            if not line:
                continue
            h, rel = line.split(' ', 1)
            fp = os.path.join(ROOT, rel)
            if not os.path.exists(fp) or sha256(fp) != h:
                bad.append(rel)
        check('V5', not bad, 'backend changed=%s' % bad)
    else:
        check('V5', False, 'baseline missing (run --snapshot)')

    # V6
    v6 = []
    if os.path.exists(SRC_VUE) and OTPAUTH in readb(SRC_VUE):
        v6.append('src')
    if os.path.isdir(DIST):
        v6 += ['dist:%s' % os.path.basename(x) for x in scan_tree(DIST, OTPAUTH)]
    check('V6', not v6, 'otpauth hits=%s' % v6)

    # V7
    bad7 = []
    for fp, want in GUARD_BASE.items():
        if not os.path.exists(fp):
            bad7.append('%s MISSING' % os.path.basename(fp))
        elif sha256(fp) != want:
            bad7.append(os.path.basename(fp))
    check('V7', not bad7, 'guards changed=%s' % bad7)

    red = [t for t, ok, _ in results if not ok]
    print('---')
    print('RED=%s' % (','.join(red) if red else 'none'))
    print('EXIT=%d' % (1 if red else 0))
    return 1 if red else 0


if __name__ == '__main__':
    sys.exit(main())
