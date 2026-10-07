#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_ipa_device.py —— 真机验证清单脚本（USDT项目 · ipa 线 · 卡 T124 第一段）

★ 定位：把 T124 的「版本覆盖清单 + 注入生效判据」编码成可机检清单。
   ★ 这是【清单脚本】—— 覆盖表与判据已落地；真机跑（读设备 iOS 版本、查 dylib 是否
     注入）需【真机】（实体资源，Owner 待提供），⛔ 无真机不硬做（见 --list 与资源闸）。

★ 覆盖清单（★ 承 Owner 裁决「两代都做、覆盖优先」+ 已确认的 pickIpa 分发表）：
   | iOS 区间         | 代际   | 内核链 | dylib 指纹 |
   |------------------|--------|--------|-----------|
   | 15.2 – 16.x      | gen3   | 无     | 470,184 B |
   | 17.0 – 17.2.1    | gen12  | 有     | 886,456 B |
   | 18.4 – 18.6.2    | gen12  | 有     | 886,456 B |
   | 18.7+            | gen3   | 无     | 470,184 B |
   | 17.3（对照）      | —      | —      | unsupported |

   ★ 18.4.2–18.6.2 归 gen12 是 Owner 已确认的扩展（原 T124 卡只写 18.4–18.4.1，现已
     按 pickIpa 分发表扩至 18.6.2）。
   ★ dylib 体积断点承 W-IOS-PKG1 §4.2 指纹实测：第 1/2 代 886,456 B（含 kexploit_opa334）
     / 第 3 代 470,184 B（无链 MCM/MHA）。

用法：
  python verify_ipa_device.py --list                       # 打印覆盖清单（无资源可跑）
  python verify_ipa_device.py --udid <udid> [--version x.y]  # 真机验证（需真机 + iproxy）
"""

import argparse
import shutil
import subprocess
import sys

# 基座 bundle id（注入前提，见 W-IOS-PKG1 §1.2 C段）
BUNDLE_ID = "com.apple.mobile.MobileHouseArrest"
DYLIB_NAME = "FilzaApplySandboxExt.dylib"

# dylib 指纹断点（承 W-IOS-PKG1 §4.2）
DYLIB_BYTES = {"gen12": 886456, "gen3": 470184}

# ★ 覆盖清单（V3 逐项；min/max 含端点，None = 无上界）
COVERAGE = [
    {"gen": "gen3",  "kernel": False, "range": "15.2 – 16.x",  "min": [15, 2, 0], "max": [16, 999999, 999999]},
    {"gen": "gen12", "kernel": True,  "range": "17.0 – 17.2.1", "min": [17, 0, 0], "max": [17, 2, 1]},
    {"gen": "gen12", "kernel": True,  "range": "18.4 – 18.6.2", "min": [18, 4, 0], "max": [18, 6, 2]},
    {"gen": "gen3",  "kernel": False, "range": "18.7+",         "min": [18, 7, 0], "max": None},
    {"gen": None,    "kernel": None,  "range": "17.3（对照·unsupported）", "min": [17, 3, 0], "max": [17, 3, 0]},
]


def cmp3(a, b):
    n = max(len(a), len(b))
    for i in range(n):
        x = a[i] if i < len(a) else 0
        y = b[i] if i < len(b) else 0
        if x != y:
            return -1 if x < y else 1
    return 0


def in_range(v, lo, hi):
    if cmp3(v, lo) < 0:
        return False
    if hi is not None and cmp3(v, hi) > 0:
        return False
    return True


def expected_for(version):
    """给定 iOS 版本，返回 COVERAGE 里命中项的期望代际；无命中返回 None。"""
    for c in COVERAGE:
        if c["gen"] is not None and in_range(version, c["min"], c["max"]):
            return c
    return None


def list_coverage():
    print("=== T124 真机验证覆盖清单（Owner 已确认分发表）===")
    for c in COVERAGE:
        dylib = f'{DYLIB_BYTES[c["gen"]]} B' if c["gen"] else "—"
        kernel = "有" if c["kernel"] else ("无" if c["kernel"] is False else "—")
        print(f'  {c["range"]:24s} → {c["gen"] or "unsupported":8s}  内核链={kernel:2s}  dylib={dylib}')
    print(f"  注入前提 bundle id：{BUNDLE_ID}")
    print(f"  注入 dylib：{DYLIB_NAME}")
    return 0


def device_ios_version(args):
    """读真机 iOS 版本。★ 需真机（iproxy/libimobiledevice 或 ssh），骨架级，未实测。"""
    if args.ssh:
        try:
            out = subprocess.check_output(
                ["ssh", args.ssh, "defaults read /System/Library/CoreServices/SystemVersion ProductVersion"],
                text=True, timeout=30,
            )
            return out.strip().split(".")
        except Exception as e:
            print(f"[verify] 读真机版本失败（ssh {args.ssh}）：{e}", file=sys.stderr)
            return None
    if args.udid:
        # ★ libimobiledevice：ideviceinfo -k ProductVersion -u <udid>（未实测）
        print("[verify] ★ 需真机 + libimobiledevice（ideviceinfo）读取 iOS 版本（未实测）", file=sys.stderr)
        return None
    print("[verify] 未给 --udid/--ssh ⇒ 无真机，不能验证", file=sys.stderr)
    return None


def verify_device(args):
    version = device_ios_version(args)
    if version is None:
        print("[verify] ★ 缺真机 ⇒ 停（等 Owner 提供真机）")
        return 2
    ver_str = ".".join(str(x) for x in version)
    exp = expected_for(version)
    print(f"[verify] 真机 iOS {ver_str} → 期望：{exp['range'] if exp else 'unsupported'}"
          f"（gen={exp['gen'] or 'unsupported'}）")
    if exp is None:
        print("[verify] 对照区间（17.3）或未覆盖：预期 unsupported，真机应不注入。")
        # ★ 逐项真机检查（未实测）：此处仅出判据，真机跑属第二段。
        return 0
    # ★ 以下三项注入生效判据需真机执行（未实测，第二段再跑）：
    #   ① bundle id 已安装（ideviceinstaller -l 含 BUNDLE_ID）
    #   ② 应用 Frameworks/ 下存在 DYLIB_NAME（ssh ls）
    #   ③ dylib 体积 == DYLIB_BYTES[exp['gen']]（± 容差）
    print(f"[verify] 注入生效判据（真机跑，未实测）：")
    print(f"  ① 已装 bundle id = {BUNDLE_ID}")
    print(f"  ② Frameworks/{DYLIB_NAME} 存在")
    print(f"  ③ dylib 体积 = {DYLIB_BYTES[exp['gen']]} B（{exp['gen']}）")
    print("[verify] ★ 需真机执行以上三项（第二段）。")
    return 0


def main():
    ap = argparse.ArgumentParser(description="真机验证清单脚本（T124 第一段）")
    ap.add_argument("--list", action="store_true", help="打印覆盖清单（无资源可跑）")
    ap.add_argument("--udid", help="真机 UDID（libimobiledevice）")
    ap.add_argument("--ssh", help="真机 ssh 目标（user@host）")
    ap.add_argument("--version", help="显式指定 iOS 版本（x.y.z），跳过设备读取")
    args = ap.parse_args()

    if args.list:
        return list_coverage()
    if args.version:
        parts = args.version.split(".")
        v = [int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0]
        exp = expected_for(v)
        print(f"[verify] 显式版本 iOS {'.'.join(map(str, v))} → "
              f"{exp['range'] if exp else 'unsupported'}")
        return 0
    return verify_device(args)


if __name__ == "__main__":
    sys.exit(main())
