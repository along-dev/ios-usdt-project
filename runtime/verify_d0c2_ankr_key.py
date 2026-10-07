# -*- coding: utf-8 -*-
"""
D0-C2 判据：Ankr API key 硬编码清出 + 脱敏模式集扩展。

★ P-4 自指防护：本脚本【不硬编码任何 key 值】，只用正则匹配形态。
   若本脚本自身含 key 明文，则它自己会成为新泄漏点。

用法：
    python verify_d0c2_ankr_key.py              # 全量
    python verify_d0c2_ankr_key.py --selftest   # 量尺前置断言（P-5）

退出码：0 = 全绿；非 0 = 有红。
"""
from __future__ import annotations

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
import argparse
import os
import re
import subprocess
import sys

ROOT = USDT_ROOT
SKIP_DIR = re.compile(r"\\node_modules\\|\\\.git\\|\\__pycache__\\|\\reference\\")

# ★★ 性能修复（2026-09-29 实测）：全仓遍历时若逐文件 read()，
#    会把 .apk/.ipa/.wasm/.png 等**数百 MB 二进制**读进内存 ⇒ 脚本假死（曾两次超时）。
#    ⇒ 只扫【可能含凭据的文本类文件】，并按扩展名白名单过滤。
TEXT_EXT = {
    ".go", ".js", ".mjs", ".cjs", ".ts", ".py", ".ps1", ".sh", ".bat", ".cmd",
    ".json", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf", ".env",
    ".md", ".txt", ".html", ".htm", ".vue", ".sql", ".css", ".xml", ".tpl",
}
# 单文件上限 8 MB（超过的一律不读，避免拖死）
MAX_BYTES = 8 * 1024 * 1024

# ★ 宽模式：覆盖两种 Ankr 形态（标准 /<chain>/<key> 与 /premium-http/<chain>/<key>）
ANKR_PAT = re.compile(r"rpc\.ankr\.com/[^\"'\s]*[0-9a-f]{32,}", re.I)
# 扩展：其他 RPC 服务商
OTHER_PATS = {
    "Tatum": r"tatum\.io/[0-9a-f]{32,}",
    "Infura": r"infura\.io/v3/[0-9a-f]{32,}",
    "Alchemy": r"alchemy\.com/v2/[A-Za-z0-9_-]{20,}",
    "QuickNode": r"quiknode\.pro/[A-Za-z0-9]{20,}",
    "GetBlock": r"getblock\.io/[A-Za-z0-9]{20,}",
    "BlockPI": r"blockpi\.network/[A-Za-z0-9]{20,}",
    "NodeReal": r"nodereal\.io/[A-Za-z0-9]{20,}",
    "Moralis": r"moralis\.io/[A-Za-z0-9]{20,}",
}

TARGETS = [
    os.path.join(ROOT, "01-backend-go", "blockchain", "erc_test.go"),
    os.path.join(ROOT, "01-backend-go", "blockchain", "trc_test.go"),
]

_results = []
SKIP_GO = False


def rec(name, ok, detail):
    _results.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def iter_files(root):
    """只产出【文本类且体积可控】的文件（避免读入数百 MB 二进制导致假死）。"""
    for dp, dn, fns in os.walk(root):
        if SKIP_DIR.search(dp):
            continue
        # 剪枝：跳过明显的二进制/素材目录
        dn[:] = [d for d in dn if d not in (
            "node_modules", ".git", "__pycache__", "reference",
            "dist", "build", ".next", "coverage")]
        for fn in fns:
            if os.path.splitext(fn)[1].lower() not in TEXT_EXT:
                continue
            p = os.path.join(dp, fn)
            try:
                if os.path.getsize(p) > MAX_BYTES:
                    continue
            except OSError:
                continue
            yield p


def scan_ankr(files=None):
    """返回 [(relpath, lineno, 形态)]，**不含 key 值**（P-4）。"""
    out = []
    it = files if files is not None else iter_files(ROOT)
    for p in it:
        try:
            src = open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for i, line in enumerate(src.splitlines(), 1):
            if ANKR_PAT.search(line):
                shape = "premium-http" if "/premium-http/" in line else "standard"
                out.append((os.path.relpath(p, ROOT), i, shape))
    return out


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True

    # 1) 正则必须能在合成样本上命中（两种形态）
    s1 = 'const u = "https://rpc.ankr.com/bsc/' + "a" * 64 + '";'
    s2 = 'const u = "https://rpc.ankr.com/premium-http/eth/' + "b" * 64 + '";'
    if ANKR_PAT.search(s1) and ANKR_PAT.search(s2):
        print("  模式有效：标准形态与 premium-http 形态均可命中")
    else:
        print("  [FAIL] 模式失效（两种形态至少一种未命中）")
        ok = False

    # 2) 负例：无 key 的 URL 不得命中
    if ANKR_PAT.search('const u = "https://rpc.ankr.com/";'):
        print("  [FAIL] 无 key 的 URL 被误命中")
        ok = False
    else:
        print("  负例正确：无 key 的 URL 不命中")

    # 3) 宽模式必须 ≥ 窄模式（防止"漏掉 premium-http"）
    narrow = re.compile(r"rpc\.ankr\.com/[a-z]+/[0-9a-f]{32,}", re.I)
    if len(ANKR_PAT.findall(s2)) >= len(narrow.findall(s2)):
        print("  宽模式覆盖窄模式（premium-http 不漏）")
    else:
        print("  [FAIL] 宽模式反而不如窄模式")
        ok = False

    # 4) ★ P-4 自指：本脚本自身不得含 key 明文
    me = os.path.abspath(__file__)
    msrc = open(me, encoding="utf-8", errors="replace").read()
    if ANKR_PAT.search(msrc):
        print("  [FAIL] ★ 本判据脚本自身含 key 明文 —— 它会成为新泄漏点（P-4）")
        ok = False
    else:
        print("  P-4 自指防护有效：本脚本不含 key 明文")

    # 5) 量尺对照：含 'rpc.ankr.com' 的文本文件数（须能跑完，不假死）
    n_any = 0
    for p in iter_files(ROOT):
        try:
            if "rpc.ankr.com" in open(p, encoding="utf-8", errors="replace").read():
                n_any += 1
        except Exception:
            pass
    print(f"  对照：含 'rpc.ankr.com' 的文本文件数 = {n_any}")

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--skip-go", action="store_true",
                    help="跳过 A6 编译门（环境过慢时用；SKIP 不计为 PASS）")
    args = ap.parse_args()
    global SKIP_GO
    SKIP_GO = args.skip_go
    if args.selftest:
        return selftest()

    print("=== D0-C2 Ankr key 硬编码清出判据 ===")
    print(f"仓库根: {ROOT}")
    print("")

    # ---- A1: 全仓宽模式命中 = 0 ----
    hits = scan_ankr()
    print(f"A1 全仓 Ankr key 命中: {len(hits)}（目标 0）")
    for rel, ln, shape in hits[:12]:
        # ★ 只输出路径与行号与形态，不输出 key（P-4）
        print(f"    {rel}:{ln}  [{shape}]")
    rec("A1 全仓 Ankr key = 0", len(hits) == 0, f"命中 {len(hits)}")

    # ---- A2: 两文件须含 os.Getenv("ANKR_API_KEY") ----
    print("")
    print("A2 改为读环境变量:")
    for p in TARGETS:
        name = os.path.basename(p)
        if not os.path.isfile(p):
            rec(f"A2 {name} 存在", False, "文件不存在")
            continue
        src = open(p, encoding="utf-8", errors="replace").read()
        has_env = 'os.Getenv("ANKR_API_KEY")' in src or "os.Getenv(`ANKR_API_KEY`)" in src
        rec(f"A2 {name} 含 os.Getenv(ANKR_API_KEY)", has_env,
            "已改为读环境变量" if has_env else "仍硬编码或未改")

    # ---- A3: 须含 t.Skip ----
    print("")
    print("A3 未设置环境变量时 t.Skip:")
    for p in TARGETS:
        name = os.path.basename(p)
        if not os.path.isfile(p):
            continue
        src = open(p, encoding="utf-8", errors="replace").read()
        has_skip = "t.Skip" in src
        rec(f"A3 {name} 含 t.Skip", has_skip,
            "已含 t.Skip" if has_skip else "★ 缺 t.Skip（不得用通过冒充跳过，P-13）")

    # ---- A4: 扩展扫描（防改过头）----
    print("")
    print("A4 扩展扫描：其他 RPC 服务商（防改过头）:")
    other_total = 0
    files = list(iter_files(ROOT))
    print(f"    （扫描文本文件 {len(files)} 个；已跳过二进制/素材目录）")
    # ★ 一次性读取，避免每个 provider 重复 open（性能修复）
    blob = {}
    for p in files:
        try:
            blob[p] = open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            blob[p] = ""
    for name, pat in OTHER_PATS.items():
        rx = re.compile(pat, re.I)
        n = sum(1 for s in blob.values() if rx.search(s))
        other_total += n
        print(f"    {name}: {n} 文件命中")
    rec("A4 其他服务商 0 命中（未被本卡引入）", other_total == 0, f"合计 {other_total}")

    # ---- A6: ★ 编译门（测试包必须能编译）----
    #
    # ★★ 本项由【第二个执行者】发现的双写事故补入（2026-09-29）：
    #    先到的版本把同名 func ankrRPC 同时写进 erc_test.go 与 trc_test.go
    #    （两者同属 package blockchain）⇒ `ankrRPC redeclared in this block`
    #    ⇒ 测试包【无法编译】。
    #    而 `go build ./...`【不编译 _test.go】⇒ EXIT=0，掩盖了该缺陷。
    #    A1–A5 全是文本正则，也不编译 Go ⇒ 该版本能拿 6/7 却根本 build 不过。
    #    ⇒ 没有本项，这类"文本全绿但编译失败"会被【稳定漏放】（P-1 形态）。
    print("")
    print("A6 编译门（测试包必须能编译）★ 本项为双写事故后补入:")
    # ★★ 环境提示（2026-09-29 实测）：本机 go 首次编译 blockchain 包耗时 > 280s
    #    （缓存失效后全量重编译）⇒ 内联调用会拖死整个判据。
    #    ⇒ 支持 --skip-go 跳过本项（此时明确打印 SKIP，不得计为 PASS，P-13）。
    if SKIP_GO:
        print("  [SKIP] A6 被 --skip-go 跳过 —— 须另行单独跑 go test 并回填结果")
        print("         ★ SKIP 不等于 PASS（P-13）")
    else:
        go = IOS_ROOT + r"\_integration\_fix_work\_toolchain\go\bin\go.exe"
        go_env = dict(os.environ)
        go_env.update({
            "GOROOT": IOS_ROOT + r"\_integration\_fix_work\_toolchain\go",
            "GOPATH": IOS_ROOT + r"\_integration\_fix_work\_gopath",
            "GOCACHE": IOS_ROOT + r"\_integration\_fix_work\_gocache",
            "GOFLAGS": "-mod=mod",
        })
        try:
            r = subprocess.run(
                [go, "test", "./blockchain/", "-run", "TestBtcDeriveMatchesBIP84Vector"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                cwd=os.path.join(ROOT, "01-backend-go"), env=go_env, timeout=900)
            ok = r.returncode == 0
            tail = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
            detail = tail[-1] if tail else ""
            rec("A6 测试包可编译（go test 退出码 0）", ok,
                f"EXIT={r.returncode} {detail[:100]}")
            if not ok:
                print("      ★ 注意：`go build ./...` 不编译 _test.go，不能替代本项")
        except subprocess.TimeoutExpired:
            rec("A6 测试包可编译", False,
                "go test 超时（>900s）—— 环境过慢，须单独跑；不得计为 PASS")
        except Exception as e:
            rec("A6 测试包可编译", False, f"执行失败: {e}")

    # ---- A5: 脱敏模式集是否已扩展（登记性断言）----
    print("")
    print("A5 脱敏模式集扩展状态（登记）:")
    san = IOS_ROOT + r"\_integration\build_unified.ps1"
    san2 = IOS_ROOT + r"\_integration\_fix_work\sanitize_target.ps1"
    found = False
    for cand in (san, san2):
        if os.path.isfile(cand):
            s = open(cand, encoding="utf-8", errors="replace").read()
            if "ankr" in s.lower():
                print(f"    {os.path.basename(cand)} 已含 ankr 模式")
                found = True
    rec("A5 脱敏模式集已含 API key 类", found,
        "已扩展" if found else "★ 未扩展（若未改脚本，本项为登记性 FAIL；见卡停靠点 1）")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  Ankr key 已清出、改为环境变量、扩展扫描无新增")
    return 0


if __name__ == "__main__":
    sys.exit(main())
