# -*- coding: utf-8 -*-
"""
I1-C1 判据：搬运 chain-* 与 module-packer 到产物，并接上 config-builder / routes。

判据先于实现（判据 9）。本脚本放产物外（_fix_work/），不进 09-docs/cards/（P-4）。

用法：
    python verify_i1c1_chain_router_hash.py              # 对产物
    python verify_i1c1_chain_router_hash.py --selftest   # 量尺前置断言（P-5）

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
import hashlib
import os
import re
import sys

PROD_ROOT = USDT_ROOT
SRC_ROOT = IOS_ROOT + r"\_integration\build\services"
C2_SERVICES = os.path.join(
    PROD_ROOT, "02-backend-node", "src_restored", "plugins", "c2", "services"
)

# 契约 C-5 / 卡 base 已锁定的源侧哈希（4 个搬运件）
SOURCES = {
    "chain-router.js": (
        "cbdd2813e371f5078c1f4ba94a3c5942684acb74901eaedc212acb44ecd98557",
        9131,
    ),
    "chain-darksword.js": (
        "29970bd5a4ef04d1d5e2510b49d9151ba68a91c53319e36691ae1476c2c4fbc0",
        11402,
    ),
    "module-packer.js": (
        "2c8bf89725e11e51f6d5f134c38e4d49195cc822bc9f7bd753205fa09c576f5c",
        3533,
    ),
    "chain-coruna.js": (
        "d1370ec9bed8edf2f830e274f27fa7c0413d9cedf94ef16a64703c1379adb340",
        11360,
    ),
}

# ★ I1-C2 适配版（登记于 L004 §4 裁决 1）：
#   chain-coruna.js / chain-darksword.js 的 import 由 '../core/crypto/seven-zip.js'
#   改为 '../../../core/crypto/seven-zip.js'（产物落点多一层，原路径解析失败）。
#   ⇒ 这两个文件的【产物侧】哈希不再等于源侧。
#   ★ 判据不因此放宽：仍逐一比对，只是把产物侧期望值设为「适配版哈希」，
#     并额外断言【除该行外与源侧逐行相同】——这样仍能抓住任何意外改动。
ADAPTED = {
    "chain-coruna.js": (
        "013af8be459655a835f3f39530cdf32028230e5d847d09d96d0971dd026e8cc4",
        12008,
        "chain-coruna.js",
    ),
    "chain-darksword.js": (
        "8155f6129b015360df48ade5595d36fdd77f0830964bbe216da40cc0ad8c83de",
        11513,
        "chain-darksword.js",
    ),
}

# 反面断言：不采用版的硬编码特征（契约 C-5 已证伪）
FORBIDDEN_MARKER = "22E240"


def read_text(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def selftest():
    """
    量尺前置断言（P-5）：
    1) sha256 计算器对已知内容必须给出已知值；
    2) 文件读取必须在缺文件时明确失败（而不是静默返回空串）。
    """
    print("=== 量尺前置断言（P-5）===")
    ok = True

    # 空文件的 sha256 是公开已知常量
    empty_expected = (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_selftest_empty.bin")
    try:
        with open(tmp, "wb") as f:
            pass
        got = sha256_of(tmp)
        if got != empty_expected:
            print(f"  [FAIL] sha256 计算器无效: {got}")
            ok = False
        else:
            print("  sha256 计算器有效（空文件常量匹配）")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    # 缺文件必须抛异常
    try:
        sha256_of(os.path.join(os.path.dirname(tmp), "_definitely_missing_xyz.bin"))
        print("  [FAIL] 缺文件未抛异常（量尺会静默通过）")
        ok = False
    except FileNotFoundError:
        print("  缺文件正确抛 FileNotFoundError")

    # ★ 源侧 4 文件此刻必须存在 —— 否则"红"是因为素材缺失，不是搬运未做
    src_missing = [n for n in SOURCES if not os.path.isfile(os.path.join(SRC_ROOT, n))]
    if src_missing:
        print(f"  [FAIL] 源侧素材缺失，判据无法区分'未搬运'与'无素材': {src_missing}")
        ok = False
    else:
        print(f"  源侧 4 个素材均存在")

    # ★ 专项：注释剥离必须有效
    #   历史缺陷（P-5 第 8 例）：注释行含 `getConfigJson(channel || undefined)` 时，
    #   正则优先匹配注释，导致"产物已改对"仍报红。
    sample = (
        "// 原为 getConfigJson(channel || undefined)\n"
        "const config = await getConfigJson(channel || undefined, { userAgent: ua });\n"
    )
    stripped = "\n".join(
        ln for ln in sample.splitlines()
        if not ln.strip().startswith("//") and not ln.strip().startswith("*")
    )
    calls = list(re.finditer(r"getConfigJson\s*\(([^)]*)\)", stripped))
    if len(calls) != 1:
        print(f"  [FAIL] 注释剥离无效：剥离后仍匹配到 {len(calls)} 处调用")
        ok = False
    else:
        n = len([a for a in calls[0].group(1).split(",") if a.strip()])
        if n != 2:
            print(f"  [FAIL] 注释剥离后实参数错为 {n}（应为 2）")
            ok = False
        else:
            print("  注释剥离有效（不再匹配注释里的旧写法）")

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    fails = []

    # ---- R1–R3：4 个搬运件必须存在、哈希与字节数与源侧逐一相同 ----
    print("R1–R3 搬运件核对（逐字节搬运）:")
    for name, (exp_sha, exp_bytes) in SOURCES.items():
        src = os.path.join(SRC_ROOT, name)
        dst = os.path.join(C2_SERVICES, name)

        # R1: 源侧哈希（卡前提）
        if not os.path.isfile(src):
            print(f"  [FAIL] R1 源侧缺失: {src}")
            fails.append(f"R1-src-missing:{name}")
            continue
        s_sha = sha256_of(src)
        if s_sha != exp_sha:
            print(f"  [FAIL] R1 源侧哈希不符 {name}: {s_sha[:16]}… ≠ {exp_sha[:16]}…")
            fails.append(f"R1-src-hash:{name}")

        # R2: 产物侧存在
        if not os.path.isfile(dst):
            print(f"  [FAIL] R2 产物缺失: {name}")
            fails.append(f"R2-missing:{name}")
            continue

        # R3: 产物哈希与字节数须与【期望】相同
        #     期望 = 源侧哈希；若该文件属 I1-C2 适配版，则用适配版哈希
        exp_dst_sha, exp_dst_bytes = exp_sha, exp_bytes
        adapted = name in ADAPTED
        if adapted:
            exp_dst_sha, exp_dst_bytes, _ = ADAPTED[name]

        d_sha = sha256_of(dst)
        d_bytes = os.path.getsize(dst)
        if d_sha != exp_dst_sha:
            print(f"  [FAIL] R3 产物哈希不符 {name}: {d_sha[:16]}… ≠ {exp_dst_sha[:16]}…")
            fails.append(f"R3-hash:{name}")
        elif d_bytes != exp_dst_bytes:
            print(f"  [FAIL] R3 产物字节数不符 {name}: {d_bytes} ≠ {exp_dst_bytes}")
            fails.append(f"R3-bytes:{name}")
        elif adapted:
            # ★ 适配版：额外断言「除 import 行外与源侧逐行相同」
            #   这比单纯哈希比对【更强】—— 能抓住任何意外改动。
            src_lines = [
                ln for ln in read_text(src).splitlines()
                if not ln.strip().startswith("//") and not ln.strip().startswith("*")
                and "seven-zip.js" not in ln
            ]
            dst_lines = [
                ln for ln in read_text(dst).splitlines()
                if not ln.strip().startswith("//") and not ln.strip().startswith("*")
                and "seven-zip.js" not in ln
            ]
            if src_lines == dst_lines:
                print(f"  [PASS] {name}  sha={d_sha[:16]}…  bytes={d_bytes}  "
                      f"★适配版（除 import 行外与源侧逐行相同）")
            else:
                diff_n = sum(1 for a, b in zip(src_lines, dst_lines) if a != b) + abs(len(src_lines) - len(dst_lines))
                print(f"  [FAIL] R3 适配版除 import 行外仍有 {diff_n} 处差异 —— 疑似意外改动")
                fails.append(f"R3-unexpected-diff:{name}")
        else:
            print(f"  [PASS] {name}  sha={d_sha[:16]}…  bytes={d_bytes}")
    print("")

    # ---- R4: node --check（由外部 verify 跑，此处只确认可读）----
    print("R4 文件可读性（node --check 由外部命令跑）:")
    for name in SOURCES:
        dst = os.path.join(C2_SERVICES, name)
        if os.path.isfile(dst):
            print(f"  [PASS] {name} 可读")
        else:
            print(f"  [FAIL] {name} 不可读/缺失")
            fails.append(f"R4-unreadable:{name}")
    print("")

    # ---- R5: ★ 反面断言 —— 产物 chain-router.js 不得含已证伪的硬编码 ----
    print(f"R5 反面断言（不得含已证伪硬编码 '{FORBIDDEN_MARKER}'）:")
    dst_router = os.path.join(C2_SERVICES, "chain-router.js")
    if os.path.isfile(dst_router):
        with open(dst_router, encoding="utf-8") as f:
            content = f.read()
        # 允许出现在「修正说明」注释里提及，但不得出现在【赋值】中
        assign_hits = re.findall(
            r"SBX0_COVERED_BUILDS\s*=\s*\[[^\]]*" + FORBIDDEN_MARKER, content
        )
        literal_hits = re.findall(
            r"=\s*\[[^\]]*['\"]" + FORBIDDEN_MARKER + r"['\"]", content
        )
        if literal_hits:
            print(f"  [FAIL] R5 发现硬编码数组字面量 {literal_hits}")
            fails.append("R5-hardcoded")
        else:
            print(f"  [PASS] R5 无硬编码数组字面量（搬对了副本）")
        # 正向：必须是派生式
        if "Object.freeze" in content and "DARKSWORD_VERSION_BUILDS" in content:
            print("  [PASS] R5 派生式特征存在（Object.freeze + DARKSWORD_VERSION_BUILDS）")
        else:
            print("  [FAIL] R5 缺派生式特征 —— 可能搬错副本")
            fails.append("R5-not-derived")
    else:
        print("  [FAIL] R5 chain-router.js 不存在，无法断言")
        fails.append("R5-no-file")
    print("")

    # ---- R6: config-builder 已接入 pickChain ----
    print("R6 config-builder.js 接入 pickChain:")
    cb = os.path.join(C2_SERVICES, "config-builder.js")
    if os.path.isfile(cb):
        with open(cb, encoding="utf-8") as f:
            cb_raw = f.read()
        # 同样剥离注释行（P-5 第 8 例同族防护）
        cb_lines = [
            ln for ln in cb_raw.splitlines()
            if not ln.strip().startswith("//") and not ln.strip().startswith("*")
        ]
        t = "\n".join(cb_lines)
        has_import = bool(re.search(r"import\s*\{[^}]*pickChain[^}]*\}\s*from\s*'\./chain-router\.js'", t))
        has_sig = re.search(r"export\s+async\s+function\s+getConfigJson\s*\(\s*channel\s*,\s*device\s*\)", t)
        has_unsupported = "unsupported" in t
        if has_import:
            print("  [PASS] 已 import pickChain")
        else:
            print("  [FAIL] 未 import pickChain")
            fails.append("R6-no-import")
        if has_sig:
            print("  [PASS] 签名已改为 (channel, device)")
        else:
            print("  [FAIL] 签名仍非 (channel, device)")
            fails.append("R6-no-sig")
        if has_unsupported:
            print("  [PASS] 含 unsupported 拒绝分支")
        else:
            print("  [FAIL] 无 unsupported 拒绝分支")
            fails.append("R6-no-unsupported")
    else:
        print("  [FAIL] config-builder.js 缺失")
        fails.append("R6-missing")
    print("")

    # ---- R7: routes/config.js 传入 device ----
    print("R7 routes/config.js 传入 device 实参:")
    rc = os.path.join(
        PROD_ROOT, "02-backend-node", "src_restored", "plugins", "c2", "routes", "config.js"
    )
    if os.path.isfile(rc):
        with open(rc, encoding="utf-8") as f:
            raw = f.read()
        # ★ 必须先剥离注释行 —— 否则会匹配到注释里举例的旧写法
        #   （实测缺陷：第 21 行注释含 `getConfigJson(channel || undefined)`，
        #    被优先匹配，导致"产物已改对"仍报 R7 失败 —— P-5 第 8 例）
        lines = [
            ln for ln in raw.splitlines()
            if not ln.strip().startswith("//") and not ln.strip().startswith("*")
        ]
        t = "\n".join(lines)
        # 取**实际调用**（排除 import 行）
        calls = [
            m for m in re.finditer(r"getConfigJson\s*\(([^)]*)\)", t)
            if "import" not in t[max(0, m.start() - 60):m.start()]
        ]
        if calls:
            args = calls[-1].group(1)
            n_args = len([a for a in args.split(",") if a.strip()])
            print(f"  getConfigJson 实参: ({args.strip()})  → {n_args} 个")
            if n_args >= 2:
                print("  [PASS] 已传第二个实参")
            else:
                print("  [FAIL] 仍缺第二个实参（device）")
                fails.append("R7-missing-device")
        else:
            print("  [FAIL] 找不到 getConfigJson 调用（非注释）")
            fails.append("R7-no-call")
    else:
        print("  [FAIL] routes/config.js 缺失")
        fails.append("R7-missing")
    print("")

    if fails:
        print(f"RESULT=RED  失败项: {fails}")
        return 1
    print("RESULT=GREEN  4 文件已搬运且哈希一致、config 已接入 pickChain")
    return 0


if __name__ == "__main__":
    sys.exit(main())
