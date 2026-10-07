# -*- coding: utf-8 -*-
"""D2-C4 实施：搬运 5 个唯一 APK 到 06-android/apk/{japapp,samples}/ + 写 manifest。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib
import os

M = IOS_ROOT
AND = USDT_ROOT + r"\06-android\apk"
J = os.path.join(AND, "japapp")
S = os.path.join(AND, "samples")

PLAN = [
    # (源, 目标目录, 目标文件名, 用途)
    (os.path.join(M, r"pjuyr\all_assets\pjuyr_all_assets\japapp_milkstream\japapp.apk"),
     J, "japapp.apk", "载荷 APK"),
    (os.path.join(M, r"pjuyr\all_assets\pjuyr_all_assets\japapp_milkstream\child_milkstream.apk"),
     J, "child_milkstream.apk", "载荷 APK（子）"),
    (os.path.join(M, r"pjuyr\all_assets\pjuyr_all_assets\myavlive\myav.apk"),
     S, "myav.apk", "样本"),
    (os.path.join(M, r"recon\apk\strip.apk"),
     S, "strip.apk", "脱壳链 L1 入口样本"),
    (os.path.join(M, r"recon\apk\unpacked\inner_b.apk"),
     S, "inner_b.apk", "脱壳链 L2 产物"),
]


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main():
    os.makedirs(J, exist_ok=True)
    os.makedirs(S, exist_ok=True)

    print("=== 源 → 目标 搬运 ===")
    rows = []
    for src, dstdir, name, use in PLAN:
        dst = os.path.join(dstdir, name)
        if not os.path.isfile(src):
            print(f"  [★源缺失] {src}")
            continue
        with open(src, "rb") as fi, open(dst, "wb") as fo:
            while True:
                b = fi.read(1 << 20)
                if not b:
                    break
                fo.write(b)
        hs, hd = sha256(src), sha256(dst)
        ok = hs == hd
        sz = os.path.getsize(dst)
        rows.append((os.path.basename(dstdir), name, hd, sz, use))
        print(f"  [{'一致' if ok else '★不一致'}] {os.path.basename(dstdir)}/{name}  {hd[:16]}…  {sz:,} B  ({use})")

    # 写 manifest
    print("")
    print("=== 写 _MANIFEST.txt ===")
    for dstdir, label, title in ((J, "japapp", "投递载荷 APK"), (S, "samples", "投递样本")):
        rows_d = [r for r in rows if r[0] == label]
        lines = [
            f"# {title}清单（★ 投递物；与 06-android/reference/apk/ 的【参照】分开）",
            "# 生成：D2-C4（Owner 裁 (a)：采方案 :49-55 权威分类表，5 条唯一）",
            "# 格式：sha256  filename  bytes  用途",
        ]
        for _d, name, h, sz, use in sorted(rows_d, key=lambda x: x[1]):
            lines.append(f"{h}  {name}  {sz}  {use}")
        mf = os.path.join(dstdir, "_MANIFEST.txt")
        with open(mf, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        print(f"  {label}/_MANIFEST.txt  {os.path.getsize(mf)} B  ({len(rows_d)} 条)")

    print("")
    print("=== 终态 ===")
    for d in (J, S):
        fs = sorted(os.listdir(d))
        print(f"  {os.path.relpath(d, USDT_ROOT)}:")
        for f in fs:
            p = os.path.join(d, f)
            print(f"    {os.path.getsize(p):,} B  {f}")


if __name__ == "__main__":
    main()
