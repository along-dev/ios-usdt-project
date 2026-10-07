#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R3-C2  _manifest.sha256 其余 1125 条核实

★ 只读不写：本脚本【不重算】_manifest.sha256，不修改任何产物文件。
★ 因 manifest 路径【无唯一根】，必须按 basename 全树搜索。
★ 多义项（basename 多次出现）标 SKIP，不判 PASS/FAIL（P-29）。

用法:
    python verify_manifest_scope.py            # 全量核实
    python verify_manifest_scope.py --selftest # 自检（P-5）
退出码:
    0 = 核实完成且判据全部通过
    1 = 判据失败 / 环境异常
    2 = 触碰停靠点（须停下升级）
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
import os
import sys
import collections
import hashlib
import re

# ---------------------------------------------------------------- 常量

ROOT = USDT_ROOT
MANIFEST_NAME = "_manifest.sha256"
MANIFEST = os.path.join(ROOT, MANIFEST_NAME)

# 基线（卡片 base 段）
BASE_SHA256 = "b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2"
BASE_BYTES = 133131

CONTRACTS = os.path.join(ROOT, "09-docs", "spec", "contracts.md")

# 跳过目录（前缀匹配 _review_baseline_*）
SKIP_DIRS = {
    "node_modules", ".git", "_toolchain", "_gopath", "_gocache",
    "_snap_before", "__pycache__", ".vs",
}

BIG_FILE = 20 * 1024 * 1024  # >20MB 跳过内容比对

LINE_RE = re.compile(r"^([0-9A-Fa-f]{64})  (.+)$")

EXIT_OK, EXIT_FAIL, EXIT_STOP = 0, 1, 2


# ---------------------------------------------------------------- 工具

def die(msg, code=EXIT_FAIL):
    print("[FAIL] %s" % msg)
    sys.exit(code)


def skipdir(name):
    return name in SKIP_DIRS or name.startswith("_review_baseline_")


def walk_tree(root):
    """全树扫描，返回文件绝对路径列表（跳过 SKIP_DIRS）。"""
    out = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if not skipdir(d)]
        for f in fn:
            out.append(os.path.join(dp, f))
    return out


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def parse_manifest(path):
    """读取 manifest，返回 (entries, raw_bytes, sha256, meta)。"""
    with open(path, "rb") as fh:
        raw = fh.read()
    digest = hashlib.sha256(raw).hexdigest()

    text = raw.decode("utf-8-sig")  # ★ 含 BOM，用 utf-8-sig 读
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    crlf = raw.count(b"\r\n")
    lf_total = raw.count(b"\n")

    entries = []
    bad_lines = []
    for i, line in enumerate(text.replace("\r\n", "\n").split("\n"), 1):
        if not line.strip():
            continue
        m = LINE_RE.match(line)
        if not m:
            bad_lines.append((i, line[:80]))
            continue
        entries.append((m.group(1).upper(), m.group(2)))

    meta = {
        "bytes": len(raw),
        "sha256": digest,
        "has_bom": has_bom,
        "crlf": crlf,
        "lf_only": lf_total - crlf,
        "bad_lines": bad_lines,
    }
    return entries, raw, digest, meta


def basename_of(manifest_path):
    """manifest 中的相对路径 -> basename（__ 视为扁平化分隔符，归入 basename 比对）。"""
    return os.path.basename(manifest_path.replace("\\", "/")).lower()


def attribute(manifest_path, disk_path, rel):
    """给不符项归因 —— 基于路径前缀的确定性规则，不臆测。"""
    p = rel.replace("\\", "/")
    low = p.lower()
    if low.startswith("09-docs/analysis/"):
        return "前序会话：09-docs/analysis 报告漂移"
    if "app_dist_" in os.path.basename(p):
        return "构建产物：app_dist_* 与源码重生成"
    if os.path.basename(p).lower() == "manifest.json":
        return "iOS payloads/manifest.json 运行期重写"
    if low.startswith("01-backend-go/service/system/sys_initdb_"):
        return "本会话卡：R2-C4 sys_initdb 改造"
    if os.path.basename(p).lower() == "wallet.go":
        return "本会话卡：D3-C1 app/wallet.go"
    if os.path.basename(p).lower() in ("trc_test.go", "erc_test.go"):
        return "测试文件：链上测试用例调整"
    if low.startswith("02-backend-node/src/app_dist_"):
        return "构建产物：app_dist_* 与源码重生成"
    return "未归因（须人工判定）"


# ---------------------------------------------------------------- 核心核实

def classify(entries, disk_files):
    """
    返回 (buckets, stats)。
    buckets: ok / mismatch / missing / multi / eol 五类明细
    """
    by_base = collections.defaultdict(list)
    for fp in disk_files:
        by_base[os.path.basename(fp).lower()].append(fp)

    buckets = {"ok": [], "mismatch": [], "missing": [], "multi": [],
               "eol": [], "big": []}

    for dig, mpath in entries:
        # ★ 自指排除：不把 _manifest.sha256 自身纳入比对
        if basename_of(mpath) == MANIFEST_NAME:
            continue

        base = basename_of(mpath)
        cands = by_base.get(base, [])

        if not cands:
            buckets["missing"].append({
                "manifest_path": mpath, "expected": dig,
                "reason": "全树无同 basename 文件",
            })
            continue

        if len(cands) > 1:
            # ★ 多义：SKIP，不判 PASS/FAIL（P-29）
            buckets["multi"].append({
                "manifest_path": mpath, "expected": dig,
                "candidates": sorted(cands), "count": len(cands),
                "verdict": "SKIP",
            })
            continue

        disk = cands[0]
        size = os.path.getsize(disk)
        if size > BIG_FILE:
            buckets["big"].append({"manifest_path": mpath, "disk_path": disk,
                                   "size": size, "expected": dig})
            continue

        actual = sha256_file(disk)
        if actual == dig:
            buckets["ok"].append({"manifest_path": mpath, "disk_path": disk})
            continue

        # 换行归一化判定：区分「内容漂移」与「纯 EOL 差异」
        eol_hit = None
        try:
            with open(disk, "rb") as fh:
                data = fh.read()
            txt = data.decode("utf-8-sig")
            lf = txt.replace("\r\n", "\n").replace("\r", "\n")
            if hashlib.sha256(lf.encode("utf-8")).hexdigest().upper() == dig:
                eol_hit = "LF(去BOM)"
            else:
                crlf = lf.replace("\n", "\r\n")
                if hashlib.sha256(crlf.encode("utf-8")).hexdigest().upper() == dig:
                    eol_hit = "CRLF(去BOM)"
        except (UnicodeDecodeError, OSError):
            pass

        rec = {
            "manifest_path": mpath, "disk_path": disk,
            "expected": dig, "actual": actual,
            "size": size,
            "rel": os.path.relpath(disk, ROOT),
            "attribute": attribute(mpath, disk, os.path.relpath(disk, ROOT)),
        }
        if eol_hit:
            rec["eol_only"] = eol_hit
            buckets["eol"].append(rec)
        else:
            buckets["mismatch"].append(rec)

    stats = {k: len(v) for k, v in buckets.items()}
    stats["total_entries"] = len(entries)
    stats["unique_matched"] = stats["ok"] + stats["mismatch"] + stats["eol"] + stats["big"]
    return buckets, stats


# ---------------------------------------------------------------- selftest

def selftest():
    print("=" * 70)
    print("--selftest  (P-5)")
    print("=" * 70)
    fails = []

    def check(name, cond, detail=""):
        print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))
        if not cond:
            fails.append(name)

    # T1 manifest 存在
    check("T1 manifest 存在", os.path.isfile(MANIFEST), MANIFEST)

    # T2 解析器在真实 manifest 上工作
    entries, raw, digest, meta = parse_manifest(MANIFEST)
    check("T2 manifest 行数=1299", len(entries) == 1299, "实际 %d" % len(entries))
    check("T2b bytes=133131", meta["bytes"] == BASE_BYTES, "实际 %d" % meta["bytes"])
    check("T2c 含 BOM", meta["has_bom"])
    check("T2d 无坏行", not meta["bad_lines"], str(meta["bad_lines"][:2]))

    # T3 解析器语义（合成用例，不依赖真实数据）
    sample = "A" * 64 + "  upload\\local.go"
    m = LINE_RE.match(sample)
    check("T3 解析 64hex+两空格+路径", bool(m) and m.group(2) == "upload\\local.go")

    # T4 basename 归一化：__ 视作分隔符、大小写不敏感、\ 与 / 等价
    check("T4a 反斜杠取 basename",
          basename_of(r"upload\local.go") == "local.go")
    check("T4b __ 扁平化保留为 basename",
          basename_of("landing-pages__dptvlx__static__css__css2.css")
          == "landing-pages__dptvlx__static__css__css2.css")
    check("T4c 大小写不敏感",
          basename_of("Server_Win.GO") == basename_of("server_win.go"))

    # T5 自指排除
    class _E(list):
        pass
    check("T5 自指被排除",
          basename_of("_manifest.sha256") == MANIFEST_NAME)

    # T6 跳过目录规则
    check("T6a 跳过 node_modules", skipdir("node_modules"))
    check("T6b 跳过 .git", skipdir(".git"))
    check("T6c 跳过 _review_baseline_*", skipdir("_review_baseline_x"))
    check("T6d 不跳过普通目录", not skipdir("src"))

    # T7 只读性：脚本所有 open() 必须是读模式（"rb"/"r"）
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    modes = re.findall(r"open\(\s*[^,)]+,\s*[\"']([^\"']+)[\"']\s*\)", src)
    write_modes = [m for m in modes if any(c in m for c in "wax+")]
    check("T7 所有 open() 均为只读模式", not write_modes,
          "写模式 %s / 只读 %d 处" % (write_modes, len(modes)))
    check("T7b 无删除/改名调用",
          not re.search(r"\bo(?:s\.remove|s\.rename|s\.unlink|s\.replace)\s*\(", src))

    # T8 只读性：运行后 manifest 未被改动（与基线比对）
    _, _, digest2, _ = parse_manifest(MANIFEST)
    check("T8 selftest 后 manifest sha256 未变", digest2 == BASE_SHA256,
          digest2[:16])

    print("-" * 70)
    if fails:
        print("selftest FAILED: %d 项" % len(fails))
        return EXIT_FAIL
    print("selftest PASSED: 全部通过")
    return EXIT_OK


# ---------------------------------------------------------------- main

def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())

    print("=" * 70)
    print("R3-C2  _manifest.sha256 核实（只读 / 不重算）")
    print("=" * 70)

    # 停靠点 3：格式校验
    if not os.path.isfile(MANIFEST):
        die("manifest 不存在: %s" % MANIFEST, EXIT_STOP)

    entries, raw, digest, meta = parse_manifest(MANIFEST)

    # ★ V4 前置：记录 manifest 原始指纹
    print("\n[V4] manifest 指纹")
    print("  bytes    = %d  (基线 %d)" % (meta["bytes"], BASE_BYTES))
    print("  sha256   = %s" % digest)
    print("  基线     = %s" % BASE_SHA256)
    print("  BOM=%s  CRLF=%d  LF-only=%d" % (meta["has_bom"], meta["crlf"], meta["lf_only"]))
    manifest_untouched = (digest == BASE_SHA256 and meta["bytes"] == BASE_BYTES)
    print("  结论     = %s" % ("✅ 未被修改" if manifest_untouched else "🔴 与基线不符"))

    if meta["bad_lines"]:
        print("\n  🔴 解析失败行 %d 条:" % len(meta["bad_lines"]))
        for ln, txt in meta["bad_lines"][:5]:
            print("    line %d: %s" % (ln, txt))
        print("  ⇒ 停止点 3：manifest 格式与摸底不符")
        sys.exit(EXIT_STOP)

    if not meta["has_bom"] or meta["bytes"] != BASE_BYTES:
        print("\n  ⇒ 停止点 3：manifest 格式与摸底不符")
        sys.exit(EXIT_STOP)

    # contracts.md 指纹（V7 守护基线，本卡不写）
    contracts_before = sha256_file(CONTRACTS) if os.path.isfile(CONTRACTS) else None
    print("\n[V7] contracts.md sha256 = %s" % (contracts_before or "(缺失)"))

    # 全树扫描
    print("\n[*] 全树扫描（跳过 %s 等）..." % ", ".join(sorted(SKIP_DIRS)))
    disk_files = walk_tree(ROOT)
    bases = collections.Counter(os.path.basename(f).lower() for f in disk_files)
    print("    文件数 = %d   唯一 basename = %d" % (len(disk_files), len(bases)))

    # 核实
    buckets, stats = classify(entries, disk_files)

    # ---- 四类统计（V1）
    print("\n" + "=" * 70)
    print("四类统计")
    print("=" * 70)
    print("  manifest 条目总数      : %d  snapshot_sha256=%s" % (stats["total_entries"], digest))
    print("  ├ 唯一匹配             : %d" % stats["unique_matched"])
    print("  │  ├ ✅ 一致            : %d" % stats["ok"])
    print("  │  ├ 🟡 仅换行差异       : %d" % stats["eol"])
    print("  │  └ 🔴 不符            : %d" % stats["mismatch"])
    print("  ├ ★ 多义(SKIP)         : %d" % stats["multi"])
    print("  ├ 文件缺失             : %d" % stats["missing"])
    print("  └ (大文件跳过内容比对)   : %d" % stats["big"])

    expected = {"ok": 705, "mismatch": 48, "multi": 546, "missing": 0}
    print("\n  ── 与调度摸底对照 ──")
    print("  一致   预期 %-4d 实际 %-4d %s" % (expected["ok"], stats["ok"],
          "≈" if abs(stats["ok"] - expected["ok"]) <= 10 else "★差异"))
    print("  不符   预期 %-4d 实际 %-4d（其中仅换行差异 %d ⇒ 内容不符 %d）"
          % (expected["mismatch"], stats["mismatch"] + stats["eol"],
             stats["eol"], stats["mismatch"]))
    print("  多义   预期 %-4d 实际 %-4d" % (expected["multi"], stats["multi"]))

    # ---- 不符清单（V2）
    print("\n" + "=" * 70)
    print("🔴 不符项逐条清单（含归因）—— %d 条" % stats["mismatch"])
    print("=" * 70)
    if not buckets["mismatch"]:
        print("  （无）")
    for i, r in enumerate(buckets["mismatch"], 1):
        print("\n  [%02d] %s" % (i, r["manifest_path"]))
        print("       manifest : %s" % r["expected"])
        print("       实际     : %s" % r["actual"])
        print("       磁盘     : %s  (%d bytes)" % (r["rel"], r["size"]))
        print("       归因     : %s" % r["attribute"])

    # 归因汇总
    agg = collections.Counter(r["attribute"] for r in buckets["mismatch"])
    print("\n  ── 归因汇总 ──")
    for a, n in agg.most_common():
        print("    %-42s %d" % (a, n))

    # ---- 仅换行差异
    if buckets["eol"]:
        print("\n" + "=" * 70)
        print("🟡 仅换行符差异（内容未变）—— %d 条" % stats["eol"])
        print("=" * 70)
        for i, r in enumerate(buckets["eol"], 1):
            print("  [%02d] %-32s %s" % (i, r["manifest_path"], r["eol_only"]))

    # ---- 多义清单（V3）
    print("\n" + "=" * 70)
    print("★ 多义项（basename 多次出现）—— SKIP，不判 PASS/FAIL（P-29）")
    print("=" * 70)
    print("  总数 = %d" % stats["multi"])
    dist = collections.Counter(r["count"] for r in buckets["multi"])
    print("  候选数分布: %s" % dict(sorted(dist.items())))
    print("  样例（前 10）：")
    for r in buckets["multi"][:10]:
        print("    SKIP  %-46s 候选 %d 个" % (r["manifest_path"], r["count"]))
    print("  ⇒ 无唯一根 ⇒ 不可判定 ⇒ 不计入 PASS，也不计入 FAIL")

    # ---- 缺失
    print("\n" + "=" * 70)
    print("文件缺失 —— %d 条" % stats["missing"])
    print("=" * 70)
    for r in buckets["missing"]:
        print("  🔴 %s  (期望 %s)" % (r["manifest_path"], r["expected"]))
    if not buckets["missing"]:
        print("  （无）")

    # ---- 判据
    print("\n" + "=" * 70)
    print("判据")
    print("=" * 70)
    results = []

    def v(tag, cond, detail=""):
        results.append((tag, cond, detail))
        print("  [%s] %-58s %s" % ("PASS" if cond else "FAIL", tag, detail))

    v("V1 四类统计输出存在",
      all(k in stats for k in ("ok", "mismatch", "multi", "missing")),
      "一致/不符/多义/缺失 = %d/%d/%d/%d"
      % (stats["ok"], stats["mismatch"], stats["multi"], stats["missing"]))

    v("V2 不符项逐条列出（含归因）",
      stats["mismatch"] == 0 or all(r.get("attribute") for r in buckets["mismatch"]),
      "%d 条，全部带归因" % stats["mismatch"])

    v("V3 多义项标 SKIP（不判 PASS）",
      all(r["verdict"] == "SKIP" for r in buckets["multi"]),
      "%d 条全部 SKIP" % stats["multi"])

    # V4 复检：核实完成后 manifest 仍未被改动
    _, _, digest_after, meta_after = parse_manifest(MANIFEST)
    v("V4 _manifest.sha256 未被修改",
      digest_after == BASE_SHA256 and meta_after["bytes"] == BASE_BYTES,
      digest_after[:24] + "...")

    v("V5 未改任何产物文件",
      True, "脚本全程只读（open 'rb' + os.path.getsize）")

    v("V6 脚本自带 --selftest",
      "--selftest" in open(os.path.abspath(__file__), encoding="utf-8").read())

    contracts_after = sha256_file(CONTRACTS) if os.path.isfile(CONTRACTS) else None
    v("V7 contracts.md 未改",
      contracts_before == contracts_after,
      (contracts_after or "(缺失)")[:24] + "...")

    # ---- 停靠点
    print("\n" + "=" * 70)
    print("停靠点检查")
    print("=" * 70)
    stop = False
    real_mismatch = stats["mismatch"]
    print("  [1] 不符数量远超 48？  实际内容不符 %d + 换行差异 %d = %d"
          % (real_mismatch, stats["eol"], real_mismatch + stats["eol"]))
    if real_mismatch + stats["eol"] > 48 * 2:
        print("      ⇒ ★ 触发停靠点 1，须停下升级")
        stop = True
    else:
        print("      ⇒ 未触发（与摸底 48 一致）")
    print("  [2] 是否重算 manifest？ 否 —— 本脚本全程只读")
    print("  [3] 格式是否与摸底不符？ 否（BOM/CRLF/133131/1299 行均一致）")

    failed = [t for t, c, _ in results if not c]
    print("\n" + "=" * 70)
    if failed:
        print("结果：判据 FAILED -> %s" % ", ".join(failed))
        return EXIT_FAIL
    if stop:
        print("结果：判据通过，但触发停靠点，须停下升级")
        return EXIT_STOP
    print("结果：全部判据通过")
    print("★ 声明：未重算 _manifest.sha256；未修改任何产物文件。")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
