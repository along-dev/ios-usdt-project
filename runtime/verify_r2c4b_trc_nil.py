#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R2-C4b `trc_test.go` 的 `res` nil 解引用 —— 判据脚本（只读 + 只调用 go 工具链）。

卡：E:\\USDT项目\\09-docs\\cards\\R2-C4b-trc_test_nil解引用.md

判据（对齐卡文 §判据 表 R1~R8）：
  R1  go vet ./blockchain/ 输出【不含】trc_test.go 的 `using res`
  R2  trc_test.go 中【不存在】`res, _ :=` 形式（Do 的 err 必被接收）
  R3  trc_test.go 中【不存在】`req, _ :=` 形式
  R4  go test ./blockchain/ -run TestGetErrInfo 可编译（EXIT=0）
  R5  未设 ANKR_API_KEY 时走 t.Skip（不红）—— 防改过头用例
  R6  verify_r2c4_govet.py 的对应断言已同步更新
  R7  守护：_manifest.sha256 / contracts.md 未改（本卡禁改）
  R8  只改了本卡允许的文件（trc_test.go 之外的非测试 Go 文件未动）

退出码：0 = 全绿；1 = 有 FAIL。

★ 反「假绿」设计（对齐 P-25）：
  - R1 直接读 go vet 真实输出，不用"文件里有没有 err != nil"这种弱代理
  - R2/R3 用正则扫真实源码，且打印命中行号
  - R4/R5 跑真实 go test，并回读输出确认出现 SKIP 字样
"""
# ★ 自带 UTF-8 输出，不依赖调用方设置 PYTHONIOENCODING（P-10）
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
    pass

import hashlib
import os
import re
import subprocess
import sys

ROOT = USDT_ROOT
GO_DIR = os.path.join(ROOT, "01-backend-go")
GO_BIN = IOS_ROOT + r"\_integration\_fix_work\_toolchain\go\bin\go.exe"
GOROOT = IOS_ROOT + r"\_integration\_fix_work\_toolchain\go"
GOPATH = IOS_ROOT + r"\_integration\_fix_work\_gopath"
GOCACHE = IOS_ROOT + r"\_integration\_fix_work\_gocache"

TRC_TEST = r"01-backend-go\blockchain\trc_test.go"
BASE_TRC_TEST_SHA256 = \
    "274ce3867422d42582e6adf716c62684f2cd34a59e5c9a198b0fb666f4327373"

GOVET_PY = IOS_ROOT + r"\_integration\_fix_work\verify_r2c4_govet.py"

# ★ R8：blockchain/** 中【非目标】文件的改前基线（本卡禁改）
NON_TARGET_BASELINE = {
    r"01-backend-go\blockchain\btc.go":
        "5ec07283eb36f1007007635dd7ab7c32602932211c1fa4dc3c91d845e8f7d6ac",
    r"01-backend-go\blockchain\btc_test.go":
        "8a0f2e88fe95e8544e15f48f22956ac477a8b20294d85ab23d514bc725396a92",
    r"01-backend-go\blockchain\erc_test.go":
        "29a8d305550a43b5a35909009cbff5bb9f03b3ea9a080c3a1051eb8e4002012f",
    r"01-backend-go\blockchain\eth.go":
        "19d95f03267395e3d9ba96193c3b00f0e56a1953adfcb038336b995b64dfe6d8",
    r"01-backend-go\blockchain\scan.go":
        "bf7f6f3c1eac4ad9047bfbdb2a23750a34441800786dba5dfd23ca1710fa2de7",
    r"01-backend-go\blockchain\trx.go":
        "e266ec91c1e0c86ffa47e82f5b2ebc5c09b245c00f542b1e33d4e75700bcd120",
}

# ★ R7：守护文件改前基线（本卡禁改）
GUARD_BASELINE = {
    "_manifest.sha256":
        "b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2",
    r"09-docs\spec\contracts.md":
        "f80a2ead6736d5f5aff70e72e3aa7de1c7cc63f93a604fb6eeb4a163059f925c",
}

TARGET_WARNING_SUBSTR = r"trc_test.go:392"

BAD_PATTERNS = [
    ("R2", r"res\s*,\s*_\s*:=", "`res, _ :=`（Do 的 err 被丢弃）"),
    ("R3", r"req\s*,\s*_\s*:=", "`req, _ :=`（NewRequest 的 err 被丢弃）"),
]

RESULTS = []


def sha256_file(p):
    if not os.path.exists(p):
        return None
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_rel(rel):
    return sha256_file(os.path.join(ROOT, rel))


def go_env():
    env = dict(os.environ)
    env["GOROOT"] = GOROOT
    env["GOPATH"] = GOPATH
    env["GOCACHE"] = GOCACHE
    env["GOFLAGS"] = "-mod=mod"
    env["PATH"] = os.path.join(GOROOT, "bin") + os.pathsep + env.get("PATH", "")
    return env


def run_go(args, timeout=900):
    try:
        p = subprocess.run(
            [GO_BIN] + args,
            cwd=GO_DIR,
            env=go_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return p.returncode, p.stdout.decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return -1, "EXEC_ERROR: %r" % (e,)


def check(vid, desc, ok, detail=""):
    RESULTS.append((vid, desc, ok, detail))
    flag = "PASS" if ok else "FAIL"
    print("[%s] %s %s" % (flag, vid, desc))
    if detail:
        for line in str(detail).splitlines():
            print("        " + line)


def read_text(p):
    with open(p, "rb") as fh:
        return fh.read().decode("utf-8", "replace")


def main():
    print("=" * 74)
    print("R2-C4b `trc_test.go` 的 `res` nil 解引用 —— 判据")
    print("=" * 74)

    trc_path = os.path.join(ROOT, TRC_TEST)
    src = read_text(trc_path) if os.path.exists(trc_path) else ""
    src_lines = src.splitlines()

    # ---------- R1 ----------
    vet_code, vet_out = run_go(["vet", "./blockchain/"])
    print("\n----- go vet ./blockchain/ 原始输出 (EXIT=%s) -----" % vet_code)
    print(vet_out.rstrip() or "(无输出)")
    print("-" * 50)
    warn_hits = [l for l in vet_out.splitlines()
                 if l.strip() and TARGET_WARNING_SUBSTR in l]
    check(
        "R1",
        "go vet ./blockchain/ 不含 trc_test.go 的 `using res`（实测命中 %d 条）"
        % len(warn_hits),
        len(warn_hits) == 0,
        ("命中:\n" + "\n".join(warn_hits)) if warn_hits else "该告警已消除",
    )

    # ---------- R2 / R3 ----------
    for vid, pat, label in BAD_PATTERNS:
        hits = []
        for i, line in enumerate(src_lines, 1):
            if re.search(pat, line):
                hits.append("L%d: %s" % (i, line.strip()))
        check(
            vid,
            "trc_test.go 中不存在 %s（实测命中 %d 处）" % (label, len(hits)),
            len(hits) == 0,
            ("命中:\n" + "\n".join(hits)) if hits else "0 处 —— err 已被接收",
        )

    # ---------- R4 ----------
    test_code, test_out = run_go(
        ["test", "./blockchain/", "-run", "TestGetErrInfo", "-v"]
    )
    print("\n----- go test ./blockchain/ -run TestGetErrInfo -v 原始输出 "
          "(EXIT=%s) -----" % test_code)
    print(test_out.rstrip() or "(无输出)")
    print("-" * 50)
    compiled = ("[build failed]" not in test_out
                and "build failed" not in test_out
                and "undefined:" not in test_out)
    check(
        "R4",
        "go test ./blockchain/ -run TestGetErrInfo 可编译（实测 EXIT=%s）" % test_code,
        test_code == 0 and compiled,
        test_out.strip()[:800] if test_out.strip() else "无输出",
    )

    # ---------- R5 ----------
    key_set = bool(os.environ.get("ANKR_API_KEY", "").strip())
    if key_set:
        skip_ok = ("SKIP" in test_out) or (test_code == 0)
        detail = ("环境已设 ANKR_API_KEY ⇒ 联网分支；EXIT=%s，出现 SKIP=%s"
                  "（Do 失败亦应为 Skip 而非 FAIL）"
                  % (test_code, "SKIP" in test_out))
    else:
        skip_ok = ("SKIP" in test_out) and (test_code == 0) and \
            ("FAIL" not in test_out)
        detail = ("未设 ANKR_API_KEY ⇒ 应走 t.Skip；实测 EXIT=%s，出现 SKIP=%s，"
                  "出现 FAIL=%s"
                  % (test_code, "SKIP" in test_out, "FAIL" in test_out))
    check("R5", "未设 ANKR_API_KEY 时走 t.Skip（不红）—— 防改过头", skip_ok, detail)

    # ---------- R6 ----------
    # ★ 判据本体（不是常量定义）：检查 V2 的 check(...) 调用是否已翻转方向。
    #   常量 OUT_OF_CARD_WARNING 必须【保留】（脚本仍靠它检测告警串），
    #   故不能拿它的定义当"未同步"的证据 —— 那会误报。
    govet_ok = False
    govet_detail = "verify_r2c4_govet.py 不存在"
    if os.path.exists(GOVET_PY):
        gsrc = read_text(GOVET_PY)
        # 抽出 V2 断言块：从 '"V2",' 起取后续 12 行
        m = re.search(r'"V2"\s*,(.*?)\n\s*\)\s*\n', gsrc, re.S)
        v2_block = m.group(1) if m else ""
        # 新方向：断言"已消除" => 期望 not kept，且文案含"已由 R2-C4b 消除"
        asserts_removed = ("not kept" in v2_block) and ("已由 R2-C4b 消除" in v2_block)
        # 旧方向残留：断言 kept（存在）
        still_asserts_kept = bool(
            re.search(r'^\s*kept\s*,\s*$', v2_block, re.M)
        )
        mentions_c4b = "R2-C4b" in gsrc
        keeps_assertion = ('"V2"' in gsrc)
        govet_ok = (asserts_removed and not still_asserts_kept
                    and mentions_c4b and keeps_assertion)
        govet_detail = (
            "V2 已断言「已由 R2-C4b 消除」(not kept): %s（须 True）\n"
            "V2 旧方向残留 `kept,`               : %s（须 False）\n"
            "已出现 `R2-C4b` 留痕                : %s（须 True）\n"
            "V2 断言未被整条删除                  : %s（须 True）\n"
            "V2 断言块:\n%s"
        ) % (asserts_removed, still_asserts_kept, mentions_c4b,
             keeps_assertion,
             "\n".join("          " + l for l in v2_block.strip().splitlines()))
    check("R6", "verify_r2c4_govet.py 的对应断言已同步更新（V2 同步）",
          govet_ok, govet_detail)

    # ---------- R7 ----------
    g_bad = []
    for rel, want in GUARD_BASELINE.items():
        got = sha256_rel(rel)
        if got != want:
            g_bad.append("%s\n  want=%s\n  got =%s" % (rel, want, got))
    check("R7", "守护：_manifest.sha256、contracts.md 未改",
          len(g_bad) == 0,
          "\n".join(g_bad) if g_bad else "2/2 逐字节一致")

    # ---------- R8 ----------
    n_bad = []
    for rel, want in NON_TARGET_BASELINE.items():
        got = sha256_rel(rel)
        if got != want:
            n_bad.append("%s\n  want=%s\n  got =%s" % (rel, want, got))
    trc_now = sha256_rel(TRC_TEST)
    n_files = len(NON_TARGET_BASELINE)
    check(
        "R8",
        "只改了允许的文件：%d 个非目标 Go 文件 sha256 未变" % n_files,
        len(n_bad) == 0,
        ("\n".join(n_bad) if n_bad else "%d/%d 逐字节一致" % (n_files, n_files))
        + "\n trc_test.go sha256(baseline) : %s\n trc_test.go sha256(actual)   : %s"
        % (BASE_TRC_TEST_SHA256, trc_now),
    )

    # ---------- 汇总 ----------
    print("\n" + "=" * 74)
    passed = sum(1 for _, _, ok, _ in RESULTS if ok)
    print("汇总：%d/%d PASS" % (passed, len(RESULTS)))
    for vid, desc, ok, _ in RESULTS:
        print("  %-4s %s  %s" % (vid, "PASS" if ok else "FAIL", desc))
    print("=" * 74)
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
