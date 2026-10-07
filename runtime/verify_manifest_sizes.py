"""
A4 / P1-7 验收脚本：比对 coruna/payloads/manifest.json 的 size 字段与磁盘实际大小。

manifest 实际结构：
    { "<40-hex module hash>": [ {file, f1, f2, type, size}, ... ], ... }
    共 20 个模块、91 条 entry

文件实际位置：payloads/<module-hash>/entryN_type0xNN.{dylib,bin}

★★ 2026-09-27 修正了本脚本的两处错误前提（A4 实测）：

  ① 原文档写"若照 manifest 构造容器，size 不符会导致【错误偏移】" —— **不成立**。
     实测：容器由服务端 `payload_cdn.build_f00dbeef_container()` 构造，
     它读 `fpath.read_bytes()` 并用 `len(entry_data[i])`，
     **根本不读 manifest 的 size 字段**；两个 Stage3_Variant*.js 的 buildContainer
     只是 `fetchBin("/api/payload/container/<hash>")` 取现成容器，不本地构造。
     对全部 20 个 hash 实测构造 + `verify_f00dbeef()` 校验：**20/20 结构合法**。
     manifest.size 的唯一消费者是 `GET /api/payload/manifest`（信息展示）。

  ② 原脚本把路径硬编码为**原始素材**（§6.1 规定素材只读），
     导致"先修 manifest"这条方案自认的处置**按字面无法执行**、验收永远为 ✗。
     现改为默认校验**产物**，素材仍可显式指定以对照。

  → 本脚本检查的是【元数据自洽性】，不是"会不会产出坏容器"。

运行：
    $env:PYTHONIOENCODING='utf-8'
    python verify_manifest_sizes.py                      # 默认校验产物
    python verify_manifest_sizes.py -Target <payloads 目录>
    set CORUNA_PAYLOAD_ROOT=<dir> && python verify_manifest_sizes.py
"""
# ★ X3：本脚本【自带】UTF-8 输出，不依赖调用方设置 PYTHONIOENCODING（P-10）
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import os as _os
import sys as _sys

_os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # 旧版 Python 无 reconfigure 时静默降级
import json
import os
import sys
from collections import Counter

DEFAULT_TARGET = USDT_ROOT + r'\05-ios\coruna\payloads'                       # 产物（可修）
MATERIAL       = IOS_ROOT + r'\ios15-17版本漏洞\ios15-17版本漏洞\coruna\payloads'  # 素材（只读，仅对照）


def pick_target() -> str:
    argv = sys.argv[1:]
    for i, a in enumerate(argv):
        if a in ('-Target', '--target') and i + 1 < len(argv):
            return argv[i + 1]
    return os.environ.get('CORUNA_PAYLOAD_ROOT') or DEFAULT_TARGET


P = pick_target()
MANIFEST = os.path.join(P, 'manifest.json')

print('=' * 82)
print('coruna payloads/manifest.json  vs  磁盘实际大小')
print('=' * 82)
print('目标: %s' % P)
if os.path.normcase(os.path.abspath(P)) == os.path.normcase(os.path.abspath(MATERIAL)):
    print('      （这是【原始素材】，只读；其中 14 条 44/49 不符为本就存在的原始差异）')
print()

if not os.path.isfile(MANIFEST):
    print('manifest 不存在:', MANIFEST)
    sys.exit(2)

data = json.load(open(MANIFEST, encoding='utf-8', errors='replace'))

total = 0
mismatch = []
missing = []
no_size = []
matched = 0

for mod, entries in data.items():
    moddir = os.path.join(P, mod)
    for e in entries:
        total += 1
        fname = e.get('file')
        msize = e.get('size')
        if fname is None:
            no_size.append((mod, '<no file field>'))
            continue
        if msize is None:
            no_size.append((mod, fname))
            continue
        fp = os.path.join(moddir, fname)
        if not os.path.isfile(fp):
            missing.append((mod, fname, msize))
            continue
        actual = os.path.getsize(fp)
        if int(msize) != actual:
            mismatch.append((mod, fname, int(msize), actual))
        else:
            matched += 1

print('模块数        : %d' % len(data))
print('entry 总数    : %d' % total)
print('size 一致     : %d' % matched)
print('size 不符     : %d' % len(mismatch))
print('磁盘缺失      : %d' % len(missing))
print('缺 size 字段  : %d' % len(no_size))
print()

if mismatch:
    print('-' * 82)
    print('★ size 不符明细（元数据与磁盘不一致；容器构造不受影响，见文件头说明）')
    print('-' * 82)
    print('%-20s %-30s %10s %10s %8s' % ('模块(hash 前8)', '文件', 'manifest', '磁盘', '差'))
    for mod, fname, ms, ac in mismatch:
        print('%-20s %-30s %10d %10d %+8d' % (mod[:8], fname, ms, ac, ac - ms))
    print()
    c = Counter(f for _, f, _, _ in mismatch)
    print('按文件名聚合:')
    for k, v in c.most_common():
        print('   %-34s %d 条' % (k, v))
    print()

if missing:
    print('磁盘缺失明细（前 10）:')
    for mod, fname, ms in missing[:10]:
        print('   %s / %s (manifest size=%s)' % (mod[:8], fname, ms))
    print()

if no_size:
    print('缺字段明细:')
    for mod, fname in no_size:
        print('   %s / %s' % (mod[:8], fname))
    print()

print('=' * 82)
if mismatch or missing:
    print('结论: ✗ 存在 %d 条 size 不符、%d 条磁盘缺失' % (len(mismatch), len(missing)))
    print('      → 以磁盘为准修 manifest（不改载荷本体，符合 §6.2）；')
    print('        素材目录不可写（§6.1），请在产物目录执行。')
    sys.exit(1)
print('结论: ✓ 全部 %d 条 size 与磁盘一致（元数据自洽）' % matched)
print()
print('附：容器能否正确构造与 manifest.size 无关 —— 见文件头说明①。')
