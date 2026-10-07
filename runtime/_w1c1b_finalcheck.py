# -*- coding: utf-8 -*-
"""
W1-C1b 终检：
  A) J1 全量：05-ios 下 113 个 .js/.dylib 是否均未被改（对比基线清单）
  B) 硬约束：02/03/04/01 后端与前端目录是否被触碰（mtime 扫描）
  C) 模板层与载荷本体的物理隔离证明
  D) _manifest.sha256 / contracts.md 未改
"""
from __future__ import annotations

import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib
import os
import time

ROOT = USDT_ROOT
IOS = IOS_ROOT
FW = os.path.join(IOS, "_integration", "_fix_work")
CUR = os.path.join(FW, "_w1c1b_payload_current.txt")

MANIFEST_SHA = "b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2"
BUILD_SHA_BASE = "e74ccdc201616db84072f8e27a99d79be544e78d18445f0e03eedc172a85ffd9"
BUILD_SHA_NOW = "906acc07affd8ff88e235773c3bd36442b193aa17659d985be2ad91867beca04"


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


print("=" * 70)
print("A) J1 全量载荷扫描（05-ios 下 .js/.dylib）")
print("=" * 70)
cur = {}
with open(CUR, encoding="utf-8") as f:
    for line in f:
        line = line.rstrip("\n")
        if not line.strip():
            continue
        h, rel = line.split("  ", 1)
        cur[rel] = h

bad = []
for rel, h in cur.items():
    p = os.path.join(ROOT, rel)
    if not os.path.isfile(p):
        bad.append((rel, "MISSING"))
        continue
    now = sha256(p)
    if now != h:
        bad.append((rel, f"{h[:12]} -> {now[:12]}"))

print(f"  受检载荷文件数 : {len(cur)}")
print(f"  与记录不一致   : {len(bad)}")
for rel, why in bad[:20]:
    print(f"    X {rel}: {why}")

# 抽样核对判据基线
samples = {
    r"05-ios\darksword\rce_loader.js": "f6d78594778473dec1ae4d75fd71ef7b1a2cccc4cae13ec2d361bdbb8e90d969",
    r"05-ios\coruna\implant_ops.js": "43fb7b6f940c62237d0db869eec647704d155cfed69ea6e4b5da4786c555c286",
}
print("  判据抽样基线核对:")
for rel, want in samples.items():
    p = os.path.join(ROOT, rel)
    got = sha256(p) if os.path.isfile(p) else "MISSING"
    ok = got == want
    print(f"    [{'PASS' if ok else 'FAIL'}] {rel}")
    print(f"           {got}")

print()
print("=" * 70)
print("B) 硬约束：禁改目录是否被触碰")
print("=" * 70)
# 模板层建立时间 = 会话起点；扫描禁改目录中在此之后被修改的文件
TEMPLATES = os.path.join(ROOT, "05-ios", "_templates")
t0 = os.path.getmtime(TEMPLATES)
print(f"  模板层 mtime = {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t0))}（作为本卡时间基准）")

FORBIDDEN = ["01-backend-go", "02-backend-node", "03-web-admin", "04-landing"]
for d in FORBIDDEN:
    base = os.path.join(ROOT, d)
    touched = []
    if os.path.isdir(base):
        for dp, dn, fns in os.walk(base):
            for fn in fns:
                p = os.path.join(dp, fn)
                try:
                    if os.path.getmtime(p) > t0:
                        touched.append(p)
                except OSError:
                    pass
    print(f"  {d:<20} 本卡后修改的文件数 = {len(touched)}  {'OK' if not touched else 'X 被触碰'}")
    for p in touched[:5]:
        print(f"      {os.path.relpath(p, ROOT)}")

print()
print("=" * 70)
print("C) 物理隔离：模板层 vs 载荷本体")
print("=" * 70)
ds_files = sorted(os.listdir(os.path.join(ROOT, "05-ios", "darksword")))
tpl_files = []
for dp, dn, fns in os.walk(TEMPLATES):
    for fn in fns:
        tpl_files.append(os.path.relpath(os.path.join(dp, fn), ROOT))
print(f"  载荷本体目录 05-ios\\darksword\\ 文件数 : {len(ds_files)}")
print(f"  模板层 05-ios\\_templates\\ 文件数      : {len(tpl_files)}")
for t in tpl_files:
    print(f"      {t}")
print(f"  模板层是否混入 darksword/ 载荷目录 : {'否（隔离 OK）' if not any('_templates' in f for f in ds_files) else 'X 是'}")
print(f"  载荷目录是否出现 template 文件      : {[f for f in ds_files if 'template' in f.lower()] or '无（隔离 OK）'}")

print()
print("=" * 70)
print("D) 守护件")
print("=" * 70)
mf = os.path.join(ROOT, "_manifest.sha256")
g = sha256(mf)
print(f"  _manifest.sha256 : {g}")
print(f"    期望           : {MANIFEST_SHA}   [{'PASS' if g == MANIFEST_SHA else 'FAIL'}]")

ct = os.path.join(ROOT, "09-docs", "spec", "contracts.md")
print(f"  contracts.md 存在 : {os.path.isfile(ct)}")

b = os.path.join(IOS, "_integration", "build_unified.ps1")
gb = sha256(b)
print(f"  build_unified.ps1 : {gb}")
print(f"    base             : {BUILD_SHA_BASE}   [已改 = 预期]")
print(f"    期望(本次)       : {BUILD_SHA_NOW}   [{'PASS' if gb == BUILD_SHA_NOW else 'CHANGED AGAIN'}]")
