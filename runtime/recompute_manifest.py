# -*- coding: utf-8 -*-
"""
重算 _manifest.sha256（规则已由 174/174 实证确认）。

★ 规则（实证自现有清单）：
    app_dist_<相对路径，目录分隔符与部分字符替换为 _>.js
        ← 02-backend-node/src_restored/<相对路径>.js
    其余记录为 <相对路径>（含反斜杠）或裸文件名 —— 属其他模块，本脚本【不重算】。

★ 安全措施：
    1. 先备份原清单；
    2. 只重算【现有清单中已存在且能反推命中 src_restored 的 app_dist_* 行】；
    3. 逐行比对，输出"变更行 / 不变行 / 无法解析行"统计；
    4. 不新增、不删除任何行（保持行数与范围不变）——避免范围扩张。
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib
import os
import re
import shutil
import sys

MANIFEST = USDT_ROOT + r"\_manifest.sha256"
SR = USDT_ROOT + r"\02-backend-node\src_restored"
BACKUP = IOS_ROOT + r"\_integration\_fix_work\_backup_manifest_20260929\_manifest.sha256"

PAT = re.compile(r"^([0-9A-Fa-f]{64})(\s+)(.+)$")


def sha256_upper(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def resolve_app_dist(flat: str):
    """
    把 app_dist_a_b_c.js 反推为 src_restored 下的真实路径。
    由于原文件名可能含 _ 与 -，采用【穷举切分 + 存在性判定】。
    """
    if not flat.startswith("app_dist_") or not flat.endswith(".js"):
        return None
    body = flat[len("app_dist_"):-len(".js")]
    parts = body.split("_")
    n = len(parts)
    # 穷举：把 parts 切成若干段，段间用 \ 连接，段内用 _ 或 - 连接
    # 为避免组合爆炸，限制到 n<=8（实测最长如此）
    if n > 8:
        return None

    from itertools import product
    # 分割点：在哪些位置插入 '\'
    def splits(k):
        # 返回把 parts 分成 k 段的所有切法（段是连续子序列）
        if k == 1:
            yield [parts]
            return
        for i in range(1, len(parts) - k + 2):
            for rest in splits(k - 1):
                rest = [r for r in rest]
                # 递归后段长度需匹配
                if len(rest) == k - 1 and len(rest[0]) <= len(parts) - i:
                    yield [parts[:i]] + rest

    # 直接暴力：对 join 后的字符串，尝试把 _ 换成 \ 的 2^(n-1) 组合
    cands = set()
    for mask in range(1 << (n - 1)):
        s = parts[0]
        for i in range(n - 1):
            s += ("\\" if (mask >> i) & 1 else "_") + parts[i + 1]
        cands.add(s)
        # 同时把剩余 _ 换成 -
        cands.add(s.replace("_", "-"))
        cands.add(s.replace("_", ""))
    for c in cands:
        p = os.path.join(SR, c + ".js")
        if os.path.isfile(p):
            return p
    return None


def main():
    orig = open(MANIFEST, encoding="utf-8-sig", errors="replace").read().splitlines()
    print(f"原清单行数: {len(orig)}")

    # 备份
    os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
    shutil.copy2(MANIFEST, BACKUP)
    print(f"已备份 -> {BACKUP}")

    out = []
    n_changed = n_same = n_unresolved = n_other = 0
    changed_files = []

    for line in orig:
        m = PAT.match(line)
        if not m:
            out.append(line)
            continue
        sha, sep, name = m.group(1).upper(), m.group(2), m.group(3).strip()
        if name.startswith("app_dist_"):
            p = resolve_app_dist(name)
            if p:
                cur = sha256_upper(p)
                if cur != sha:
                    n_changed += 1
                    changed_files.append((name, sha[:12], cur[:12]))
                    out.append(f"{cur}{sep}{name}")
                else:
                    n_same += 1
                    out.append(line)
            else:
                n_unresolved += 1
                out.append(line)
        else:
            n_other += 1
            out.append(line)

    print("")
    print(f"app_dist_* 已重算且变更: {n_changed}")
    print(f"app_dist_* 已核对未变:   {n_same}")
    print(f"app_dist_* 无法反推:     {n_unresolved}")
    print(f"非 app_dist_*（保持原样）: {n_other}")
    print("")
    if changed_files:
        print("变更明细:")
        for name, old, new in changed_files:
            print(f"   {name}")
            print(f"      {old}... -> {new}...")

    # 字节级保真：保留 BOM（原文件首行有 \ufeff）
    raw0 = open(MANIFEST, "rb").read()
    has_bom = raw0[:3] == b"\xef\xbb\xbf"
    eol_crlf = b"\r\n" in raw0
    print("")
    print(f"原文件 BOM={has_bom} CRLF={eol_crlf}")

    content = "\n".join(out)
    if eol_crlf:
        content = content.replace("\n", "\r\n")
    data = content.encode("utf-8")
    if has_bom:
        data = b"\xef\xbb\xbf" + data

    with open(MANIFEST + ".new", "wb") as f:
        f.write(data)
    print(f"已写出候选: {MANIFEST}.new ({len(data)} B)")
    print("★ 未覆盖原文件 —— 需人工确认后再替换。")

    # 行数必须一致
    new_lines = open(MANIFEST + ".new", encoding="utf-8-sig", errors="replace").read().splitlines()
    print("")
    print(f"行数校验: 原 {len(orig)} vs 新 {len(new_lines)} -> {'一致' if len(orig) == len(new_lines) else '★ 不一致!'}")


if __name__ == "__main__":
    main()
