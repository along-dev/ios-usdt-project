# -*- coding: utf-8 -*-
"""精确同步：源素材 -> ios-usdt-project。
只复制【内容真有差异】或【源新增】的文件；跳过我们的运行配置/运行时目录/受保护文件。
默认演练（只列清单）；加 --apply 才真复制。"""
import os, sys, shutil, filecmp
from pathlib import Path

SRC = Path(r"G:\CTF渗透V2\IOSUSDT\USDT项目")
DST = Path(r"G:\CTF渗透V2\ios-usdt-project")
APPLY = "--apply" in sys.argv

SKIP_DIRS = {"node_modules", ".git", "logs", "log", "data", "uploads", "__pycache__",
             "_fix_work", "_auditB_work", "_d4c2_work", "_d5e1_work", "_t21_work", "_v4_captcha_probe"}
# 我们本地改过、必须保留的（源即使"不同"也不要覆盖）
PROTECT = {
    "01-backend-go/config.yaml",
    "02-backend-node/.env",
    "03-web-admin/.env.development",
    "02-backend-node/src_restored/plugins/api/routes/landing-ext.js",
    "02-backend-node/src_restored/plugins/api/middleware/auth.js",
    "03-web-admin/package.json",
    "03-web-admin/package-lock.json",
}

def norm_bytes(p):
    """读文件并归一化换行符，用于内容比较（忽略 CRLF/LF 差异）。"""
    try:
        return p.read_bytes().replace(b"\r\n", b"\n")
    except Exception:
        return None

def walk(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            full = Path(dirpath) / fn
            rel = full.relative_to(root).as_posix()
            out.append(rel)
    return out

src_files = set(walk(SRC))
dst_files = set(walk(DST))

to_copy = []      # (rel, reason)
for rel in sorted(src_files):
    if rel in PROTECT:
        continue
    if any(rel.endswith(x) for x in (".exe", ".log")):
        continue
    s = SRC / rel
    d = DST / rel
    if rel not in dst_files:
        to_copy.append((rel, "NEW"))
    else:
        if norm_bytes(s) != norm_bytes(d):
            to_copy.append((rel, "DIFF"))

print(f"源文件 {len(src_files)} | 副本文件 {len(dst_files)} | 待同步 {len(to_copy)}")
print("--- 新增(NEW) ---")
for rel, r in to_copy:
    if r == "NEW":
        print("  +", rel)
print("--- 内容差异(DIFF) ---")
for rel, r in to_copy:
    if r == "DIFF":
        print("  ~", rel)

if APPLY:
    n = 0
    for rel, r in to_copy:
        d = DST / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SRC / rel, d)
        n += 1
    print(f"\n已复制 {n} 个文件。")
else:
    print("\n(演练模式，未改动；加 --apply 执行)")

# 源新增目录提示（即使为空也提示）
src_dirs = set()
for dirpath, dirnames, _ in os.walk(SRC):
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
    if Path(dirpath) != SRC:
        src_dirs.add(Path(dirpath).relative_to(SRC).as_posix())
