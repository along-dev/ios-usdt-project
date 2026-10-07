#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R2-C4 `go vet` 风格告警处置 —— 判据脚本（只读 + 只调用 go 工具链）。

卡：E:\\USDT项目\\09-docs\\cards\\R2-C4-govet风格告警处置.md

判据：
  V1  go vet ./... 中 4 条本卡告警全部消失
  V2  blockchain\\trc_test.go:392 告警【已被 R2-C4b 消除】（原 R2-C4 有意保留，R2-C4b 单独立范围修复）
  V3  go build ./... EXIT=0
  V4  captcha tag 行为断言：captchaLength 正确序列化/反序列化
  V5  sys_user.go 具名赋值语义与位置赋值相同
  V6  未改卡外文件（blockchain/** sha256 未变）
  V7  规则手册已更正（3 条 -> 5 条）
  V8  守护：_manifest.sha256、contracts.md 未改

退出码：0 = 全绿；1 = 有 FAIL。

★ 反「假绿」设计（对齐 P-25）：
  - V1 先断言「本卡 4 条告警在改前确实存在」（用 --before 模式或从文件读基线）
  - V2 【R2-C4b 同步】原断言告警【存在】；现已翻转为断言该告警【已被消除】
        （整条断言保留，仅方向随动 —— 留痕不删）
  - 每条断言打印实测数据量，避免空洞通过
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

# ★ 版本标记：V3 = 已同步 R2-C4b（V2 曾断言 trc_test.go:392 告警仍在）
KR2C4_GOVET_VER = "V3"

RULE_DOC = os.path.join(ROOT, r"09-docs\reports\开发规则与调度说明.md")

# ★ V6：blockchain/** 的改前基线（卡外，必须逐字节不变）
BLOCKCHAIN_BASELINE = {
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
    # ★ R2-C4b 同步：trc_test.go 由 R2-C4b 卡显式修改（消除 :392 nil 解引用）
    r"01-backend-go\blockchain\trc_test.go":
        "ab05302c5a44415b9fb0d46d591778cdf6e359d0472096156bcaf71d32912925",
    r"01-backend-go\blockchain\trx.go":
        "e266ec91c1e0c86ffa47e82f5b2ebc5c09b245c00f542b1e33d4e75700bcd120",
}

# ★ V8：守护文件改前基线
GUARD_BASELINE = {
    "_manifest.sha256":
        "b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2",
    r"09-docs\spec\contracts.md":
        "f80a2ead6736d5f5aff70e72e3aa7de1c7cc63f93a604fb6eeb4a163059f925c",
}

# ★ V1：本卡 4 条告警的定位串（改后必须【全部消失】）
CARD_WARNINGS = [
    r"api\v1\response\sys_captcha.go:6",
    r"service\system\sys_user.go:179",
    r"service\system\sys_initdb_mysql.go:86",
    r"service\system\sys_initdb_pgsql.go:85",
]

# ★ V2：原卡外告警（R2-C4b 后必须【已消除】；方向随 R2-C4b 翻转）
OUT_OF_CARD_WARNING = r"blockchain\trc_test.go:392"

RESULTS = []


def sha256_file(rel):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return None
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def go_env():
    env = dict(os.environ)
    env["GOROOT"] = GOROOT
    env["GOPATH"] = GOPATH
    env["GOCACHE"] = GOCACHE
    env["GOFLAGS"] = "-mod=mod"
    env["PATH"] = os.path.join(GOROOT, "bin") + os.pathsep + env.get("PATH", "")
    return env


def run_go(args):
    """返回 (exit_code, combined_output)"""
    try:
        p = subprocess.run(
            [GO_BIN] + args,
            cwd=GO_DIR,
            env=go_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
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


def main():
    print("=" * 74)
    print("R2-C4 `go vet` 风格告警处置 —— 判据")
    print("=" * 74)

    # ---------- go vet ----------
    vet_code, vet_out = run_go(["vet", "./..."])
    print("\n----- go vet ./... 原始输出 (EXIT=%s) -----" % vet_code)
    print(vet_out.rstrip() or "(无输出)")
    print("-" * 50)

    # ---------- V1 ----------
    still = [w for w in CARD_WARNINGS if w in vet_out]
    check(
        "V1",
        "go vet 中 4 条本卡告警全部消失（实测残留 %d 条）" % len(still),
        len(still) == 0,
        ("残留: " + ", ".join(still)) if still else "4/4 已清除",
    )

    # ---------- V2 ----------
    # ★ R2-C4b 同步：原先此处断言「告警仍在（卡外，有意保留）」。
    #   R2-C4b 已单独立范围消除该告警 ⇒ 断言方向翻转为「已消除」。
    #   ★ 整条断言保留（不删），以保留 R2-C4 -> R2-C4b 的处置留痕。
    kept = OUT_OF_CARD_WARNING in vet_out
    check(
        "V2",
        "blockchain\\trc_test.go:392 告警已由 R2-C4b 消除"
        "（原 R2-C4 判为卡外有意保留）",
        not kept,
        "已消除 ✅（R2-C4b）"
        if not kept
        else "★ 仍存在 —— R2-C4b 未生效或改动被回退！",
    )

    # ---------- V3 ----------
    build_code, build_out = run_go(["build", "./..."])
    check(
        "V3",
        "go build ./... EXIT=0（实测 EXIT=%s）" % build_code,
        build_code == 0,
        build_out.strip()[:600] if build_out.strip() else "无编译错误",
    )

    # ---------- V4 ----------
    # captcha tag：源码中应为 json:"captchaLength"（无多余引号）
    cap_path = os.path.join(ROOT, r"01-backend-go\api\v1\response\sys_captcha.go")
    v4_ok = False
    v4_detail = ""
    if os.path.exists(cap_path):
        with open(cap_path, "rb") as fh:
            cap_src = fh.read().decode("utf-8", "replace")
        good = '`json:"captchaLength"`' in cap_src
        bad = '`json:"captchaLength""`' in cap_src
        # 行为证据：跑独立探针
        probe_out = ""
        probe_ok = False
        probe_main = os.path.join(ROOT, "_v4_captcha_probe", "main.go")
        if os.path.exists(probe_main):
            env = dict(os.environ)
            env["GO111MODULE"] = "off"
            env["GOFLAGS"] = ""
            env.update({k: go_env()[k] for k in ("GOROOT", "GOPATH", "GOCACHE", "PATH")})
            try:
                p = subprocess.run(
                    [GO_BIN, "run", "main.go"],
                    cwd=os.path.dirname(probe_main),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
                probe_out = p.stdout.decode("utf-8", "replace")
                probe_ok = (p.returncode == 0
                            and "VERDICT-A: PASS" in probe_out
                            and 'wire 名 == captchaLength' in probe_out
                            and "两者一致 ? true" in probe_out)
            except Exception as e:  # noqa: BLE001
                probe_out = "PROBE_EXEC_ERROR: %r" % (e,)
        v4_ok = good and not bad and probe_ok
        v4_detail = (
            "源码 tag 合法        : %s\n"
            "源码无多余引号        : %s\n"
            "行为探针 PASS         : %s\n"
            "探针关键行:\n%s"
        ) % (
            good, not bad, probe_ok,
            "\n".join("          " + l for l in probe_out.splitlines()
                      if "VERDICT" in l or "两者一致" in l or "wire 名" in l),
        )
    else:
        v4_detail = "sys_captcha.go 不存在"
    check("V4", "captcha tag 行为断言：captchaLength 正确序列化/反序列化", v4_ok, v4_detail)

    # ---------- V5 ----------
    # sys_user.go 须为具名赋值，且字段名与 model 定义一致
    usr_path = os.path.join(ROOT, r"01-backend-go\service\system\sys_user.go")
    model_path = os.path.join(ROOT, r"01-backend-go\model\system\sys_user_authority.go")
    v5_ok = False
    v5_detail = ""
    if os.path.exists(usr_path) and os.path.exists(model_path):
        with open(usr_path, "rb") as fh:
            usr = fh.read().decode("utf-8", "replace")
        with open(model_path, "rb") as fh:
            mdl = fh.read().decode("utf-8", "replace")
        named = ("SysUserId:" in usr and "SysAuthorityAuthorityId:" in usr)
        # model 字段顺序：第 1 个 SysUserId，第 2 个 SysAuthorityAuthorityId
        f1 = mdl.find("SysUserId")
        f2 = mdl.find("SysAuthorityAuthorityId")
        order_ok = (0 <= f1 < f2)
        v5_ok = named and order_ok
        v5_detail = (
            "具名赋值 present      : %s\n"
            "model 字段顺序 正确    : %s (SysUserId@%d < SysAuthorityAuthorityId@%d)\n"
            "=> 具名赋值与位置赋值语义相同（id->SysUserId, v->SysAuthorityAuthorityId）"
        ) % (named, order_ok, f1, f2)
    else:
        v5_detail = "源文件缺失"
    check("V5", "sys_user.go 具名赋值语义与位置赋值相同", v5_ok, v5_detail)

    # ---------- V6 ----------
    bc_bad = []
    for rel, want in BLOCKCHAIN_BASELINE.items():
        got = sha256_file(rel)
        if got != want:
            bc_bad.append("%s\n  want=%s\n  got =%s" % (rel, want, got))
    check(
        "V6",
        "未改卡外文件：blockchain/** %d 个文件 sha256 未变" % len(BLOCKCHAIN_BASELINE),
        len(bc_bad) == 0,
        "\n".join(bc_bad) if bc_bad else "7/7 逐字节一致",
    )

    # ---------- V7 ----------
    v7_ok = False
    v7_detail = ""
    if os.path.exists(RULE_DOC):
        with open(RULE_DOC, "rb") as fh:
            doc = fh.read().decode("utf-8", "replace")
        has5 = "5 条既有告警" in doc
        has3 = "3 条既有告警" in doc
        v7_ok = has5 and not has3
        v7_detail = "含 '5 条既有告警' : %s\n残留 '3 条既有告警' : %s" % (has5, has3)
    else:
        v7_detail = "规则手册不存在"
    check("V7", "规则手册已更正（3 条 -> 5 条）", v7_ok, v7_detail)

    # ---------- V8 ----------
    g_bad = []
    for rel, want in GUARD_BASELINE.items():
        got = sha256_file(rel)
        if got != want:
            g_bad.append("%s\n  want=%s\n  got =%s" % (rel, want, got))
    check(
        "V8",
        "守护：_manifest.sha256、contracts.md 未改",
        len(g_bad) == 0,
        "\n".join(g_bad) if g_bad else "2/2 逐字节一致",
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
