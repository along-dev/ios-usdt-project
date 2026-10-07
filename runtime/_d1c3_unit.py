# -*- coding: utf-8 -*-
"""直接单元测试 admin.js 的净化/落盘校验函数（绕过 multipart 的预净化）。

★ 目的：证明【我写的】防护独立有效，
   而不是依赖 @fastify/busboy 的 preservePath=false 默认行为。
"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import json
import subprocess
import sys
import os

ADMIN_JS = USDT_ROOT + r"\02-backend-node\src_restored\plugins\android\admin.js"

# 用 node 直接 import 这些导出函数（不启动服务）
SCRIPT = r"""
import { sanitizeApkFilename, safeJoinInside, resolveUploadDir, pickNonClobberingPath, APK_UPLOAD_MAX_BYTES, apkCandidateDirs }
  from 'file:///E:/USDT项目/02-backend-node/src_restored/plugins/android/admin.js';

const dirs = apkCandidateDirs();
console.log(JSON.stringify({ APK_UPLOAD_MAX_BYTES, dirs: dirs.map(d => d[0]) }));

const cases = [
  '../../evil.apk',
  '..\\..\\evil.apk',
  'sub/evil.apk',
  '..%2F..%2Fevil.apk',
  'evil.apk',
  'GOOD.APK',
  'noext',
  'notapk.txt',
  '.apk',
  'a\u0000b.apk',
  '',
  '..',
  'x'.repeat(300) + '.apk',
];
for (const c of cases) {
  const r = sanitizeApkFilename(c);
  console.log(JSON.stringify({ in: c.slice(0, 40), ok: r.ok, name: r.name, err: r.error }));
}

// safeJoinInside 独立验证
const base = 'C:\\tmp\\apkdir';
for (const n of ['evil.apk', '..\\evil.apk', '../evil.apk', 'sub/evil.apk', '..', 'a.apk']) {
  const r = safeJoinInside(base, n);
  console.log(JSON.stringify({ join: n, resolved: r }));
}
"""

p = subprocess.run(
    [r"E:\CTF\runtime\node\node.exe", "--input-type=module", "-e", SCRIPT],
    capture_output=True, text=True, encoding="utf-8", cwd=USDT_ROOT + r"\02-backend-node",
)
print("exit=%s" % p.returncode)
print(p.stdout)
if p.stderr:
    print("STDERR:")
    print(p.stderr[:3000])
