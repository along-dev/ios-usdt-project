#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sign_ipa.py —— IPA 签名脚本骨架（USDT项目 · ipa 线 · 卡 T123 第一段）

★ 定位：把「已注入 dylib 的 unsigned IPA」签成可 OTA 安装的 IPA（F 段）。
   ★ 这是【骨架】—— 签名流程 + 工具探测已落地；真正签名需【付费证书 .p12 + 签名工具】
     （实体资源，Owner 待提供），⛔ 无资源不硬做（见 --probe 与签名前的资源闸）。

★ 硬约束（承 W-IOS-PKG1 §1.2 F段 / README.md:84-112）：
   - bundle id 必须 = `com.apple.mobile.MobileHouseArrest`（免费账号报 9400/9401，
     改 bundle id 报 MismatchedBundleIDSigningIdentifier ⇒ 必须付费证书）。
   - 签名后 CodeDirectory identifier 须与 CFBundleIdentifier 一致。

★ 签名工具（承 W-IOS-PKG1 §2）：
   - macOS：`codesign`（官方）。
   - Windows/Linux：`zsign`（首选）/ `ldid`（备选）—— 仍需付费证书 + 匹配 bundle id。
   ★★ 下面各工具的确切命令行参数为【骨架级、未实测】—— 拿到工具后须先 `--probe`
      核对版本与参数，再放开签名闸。

用法：
  python sign_ipa.py --probe                      # 只探测工具/证书，不签名（退出码 0=工具齐）
  python sign_ipa.py --ipa in.ipa --p12 cert.p12 --password PASS [--out out.ipa] [--tool auto]
"""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile

# ★ 基座 bundle id 硬约束（签名必须匹配它）
REQUIRED_BUNDLE_ID = "com.apple.mobile.MobileHouseArrest"

# 支持的工具（探测顺序 = 优先级）
TOOLS = ["codesign", "zsign", "ldid"]


def which(tool):
    return shutil.which(tool)


def detect_tool(preferred=None):
    """探测可用签名工具，返回工具名或 None。"""
    if preferred and preferred != "auto":
        return preferred if which(preferred) else None
    for t in TOOLS:
        if which(t):
            return t
    return None


def probe(args):
    """--probe：探测工具与证书，报告资源缺口，不签名。"""
    tool = detect_tool(args.tool)
    print("[sign_ipa] tool probe:")
    for t in TOOLS:
        p = which(t)
        print(f"  [{'OK' if p else '--'}] {t:10s} {'-> ' + p if p else '(not installed)'}")
    if args.tool and args.tool != "auto":
        print(f"[sign_ipa] requested tool {args.tool}: {'available' if tool else 'unavailable'}")
    print(f"[sign_ipa] selected tool: {tool or 'none'}")
    p12_ok = bool(args.p12) and os.path.isfile(args.p12)
    print(f"[sign_ipa] cert .p12: {'OK ' + args.p12 if p12_ok else '-- missing'}")
    print(f"[sign_ipa] bundle id constraint: {REQUIRED_BUNDLE_ID} (paid cert required)")
    ready = bool(tool) and p12_ok
    print(f"[sign_ipa] result: {'resources ready' if ready else 'MISSING resources (wait for cert/tool from Owner)'}")
    return 0 if ready else 1


def sign_with_zsign(ipa, p12, password, bundle_id, out):
    """zsign 路径（单命令签整个 IPA，跨平台）。★ 参数未实测，需核对工具版本。"""
    cmd = ["zsign", "-k", p12, "-p", password, "-o", out, ipa]
    subprocess.run(cmd, check=True)


def sign_with_codesign(ipa, p12, password, bundle_id, out):
    """codesign 路径（macOS）：解包 → 逐二进制签名 → 保符号链接重打包。★ 未实测。"""
    # 1) 解包（zipfile 保留符号链接，见 ipa_pipeline 的 external_attr/symlink 处理）
    stage = out + ".stage"
    os.makedirs(stage, exist_ok=True)
    with zipfile.ZipFile(ipa) as z:
        z.extractall(stage)
    # 2) 定位 .app 并断言 bundle id
    app = None
    payload = os.path.join(stage, "Payload")
    for name in os.listdir(payload) if os.path.isdir(payload) else []:
        if name.endswith(".app"):
            app = os.path.join(payload, name)
            break
    if not app:
        raise SystemExit(f"[sign_ipa] 未在 Payload 找到 .app：{ipa}")
    # 3) 签名（identity 来自 keychain，须先 `security import cert.p12`）——
    #    ★ 此步与证书/keychain 强耦合，骨架级占位，未实测。
    subprocess.run(["codesign", "-f", "-s", "Apple Distribution: <IDENTITY>", app], check=True)
    # 4) 重打包（zip -y 语义：Python zipfile 显式设 symlink/external_attr）
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(stage):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, stage)
                z.write(full, rel)
    shutil.rmtree(stage, ignore_errors=True)


def sign(args):
    """签名主流程（资源闸在前，缺工具/证书立即退出，不静默）。"""
    tool = detect_tool(args.tool)
    if not tool:
        print(f"[sign_ipa] 无可用签名工具（codesign/zsign/ldid）⇒ 停（等 macOS 或 zsign）", file=sys.stderr)
        return 2
    if not args.p12 or not os.path.isfile(args.p12):
        print("[sign_ipa] 未提供付费证书 .p12 ⇒ 停（等 Owner 提供证书）", file=sys.stderr)
        return 2
    if not args.password:
        print("[sign_ipa] 未提供证书口令 --password ⇒ 停", file=sys.stderr)
        return 2
    if not os.path.isfile(args.ipa):
        print(f"[sign_ipa] unsigned IPA 不存在：{args.ipa}", file=sys.stderr)
        return 2
    out = args.out or args.ipa.rsplit(".", 1)[0] + "-signed.ipa"
    if tool == "codesign":
        sign_with_codesign(args.ipa, args.p12, args.password, REQUIRED_BUNDLE_ID, out)
    else:
        sign_with_zsign(args.ipa, args.p12, args.password, REQUIRED_BUNDLE_ID, out)
    print(f"[sign_ipa] 已签名：{out}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="IPA 签名脚本骨架（T123 第一段）")
    ap.add_argument("--ipa", help="已注入 dylib 的 unsigned IPA")
    ap.add_argument("--p12", help="付费证书 .p12（实体资源）")
    ap.add_argument("--password", help="证书口令")
    ap.add_argument("--out", help="输出路径（默认 <ipa>-signed.ipa）")
    ap.add_argument("--tool", default="auto", choices=["auto", "codesign", "zsign", "ldid"])
    ap.add_argument("--probe", action="store_true", help="只探测工具/证书，不签名")
    args = ap.parse_args()

    if args.probe:
        return probe(args)
    return sign(args)


if __name__ == "__main__":
    sys.exit(main())
