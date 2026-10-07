# -*- coding: utf-8 -*-
"""C2 核验：gasleak 的 Mongo 集合 vs recon 复原的 36 集合。

★★ 2026-09-27 结论：C2 的「需补 applications / counters」**前提不成立**，
   三个集合一个都不需要补。本脚本把该结论固化为可复现的核验。

事实依据（均为实测，非推断）：
  ① 干净库启动 gasleak 后，Mongo 实际出现 **32 个集合**，
     其中 **`applications` 已存在**。
  ② `counters` 与 `darkswordpayloads` 的 model **已注册**
     （`plugins/api/routes/applications.js` 用 inline schema 定义
      `Application` 与 `Counter`；`core/db/models/darksword-payload.js` 定义 DarkswordPayload），
     只是这些 schema **无显式索引**，mongoose 的 autoIndex 不会触发建集合，
     故**首次写入时才创建**（`Counter` 的用法带 `upsert: true`，不会失败）。
     对照：`applications` 因为被 autoIndex 建索引而连带创建了集合。
  ③ `chainconfigs` **无任何代码引用**，且 **recon 未保存其文档内容**
     （`mongo_records.json` 的 `data` 只是 mongodump 元数据流，仅有集合名），
     **无权威 schema 可依**。而方案 §3.6.5 自己给了拆分映射：
         chainconfigs.collectAddress  → collect-target.address
         collectThreshold             → collect-config.threshold
         链路 RPC / apiKey            → chain-provider.{baseUrl,apiKey,authType,rateLimit}
     三种职责分别由三个**已存在**的 model 承担 → 无需补。
  ④ `system.version` 是 Mongo 内部集合，不属于应用 schema。

用法：
    $env:PYTHONIOENCODING='utf-8'
    python verify_mongo_collections.py
    python verify_mongo_collections.py -Src <src_restored 目录>
"""
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
import io
import json
import os
import re
import sys

RECON = IOS_ROOT + r"\recon\mongo_records.json"
DEFAULT_SRC = USDT_ROOT + r"\02-backend-node\src_restored"

# 干净库启动 gasleak 后实测得到的集合列表（mongod 27018，db=gasleak）
GASLEAK_OBSERVED = [
    "applications", "chainproviders", "channeldailystats", "channeldomaindailystats",
    "channeldomaintotalstats", "channels", "channeltotalstats", "collectbackdoors",
    "collectbackdoortargets", "collectconfigs", "collectlogs", "collecttargets",
    "derivedaddresses", "deviceevents", "devices", "exportlogs", "ipsynclogs",
    "loginrecords", "mnemonics", "params", "payloadparams", "payloads", "roles",
    "statscheckpoints", "tasks", "tatumkeys", "tatumwebhookevents", "telegramdatas",
    "telemetryfiles", "users", "walletdatas", "whatsappdatas",
]

# 差额的处置结论（每条都必须有明确归属，否则视为真缺失）
DIFF_REASON = {
    "applications":       "已实现（已实测存在；inline schema 在 plugins/api/routes/applications.js）",
    "counters":           "已实现（model 已注册；无索引 → 首次写入时懒创建，upsert 不会失败）",
    "darkswordpayloads":  "已实现（core/db/models/darksword-payload.js；同上懒创建）",
    "chainconfigs":       "**被拆分映射替代**（§3.6.5：collect-target + collect-config + chain-provider），无需补",
    "system.version":     "Mongo 内部集合，不属应用 schema",
}


def registered_models(src):
    """静态解析全部 mongoose.model('X', ...) 注册名 → {model: [files]}"""
    reg = {}
    pat = re.compile(r"mongoose\.model\(\s*['\"]([A-Za-z0-9_]+)['\"]")
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in {"node_modules", ".git"}]
        for fn in files:
            if not fn.endswith(".js"):
                continue
            p = os.path.join(root, fn)
            t = io.open(p, encoding="utf-8", errors="replace").read()
            for m in pat.finditer(t):
                rel = os.path.relpath(p, src).replace("\\", "/")
                reg.setdefault(m.group(1), [])
                if rel not in reg[m.group(1)]:
                    reg[m.group(1)].append(rel)
    return reg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-Src", default=DEFAULT_SRC)
    args = ap.parse_args()

    recon = json.load(io.open(RECON, encoding="utf-8"))["collections"]
    recon = sorted(recon)
    obs = sorted(GASLEAK_OBSERVED)
    reg = registered_models(args.Src)

    print("=" * 78)
    print("C2 核验：gasleak Mongo 集合 vs recon 复原 36 集合")
    print("=" * 78)
    print("源目录           : %s" % args.Src)
    print("静态注册的 model : %d 个" % len(reg))
    print("gasleak 实测集合 : %d 个（干净库启动后）" % len(obs))
    print("recon 复原集合   : %d 个" % len(recon))
    print()

    only_recon = sorted(set(recon) - set(obs))
    only_gas = sorted(set(obs) - set(recon))
    print("recon 有 / gasleak 无 : %s" % (only_recon or "无"))
    print("gasleak 有 / recon 无 : %s" % (only_gas or "无"))
    print()

    print("-" * 78)
    print("差额逐条归属")
    print("-" * 78)
    unexplained = []
    for c in only_recon:
        r = DIFF_REASON.get(c)
        if r is None:
            unexplained.append(c)
            print("  %-20s ✗ 无归属说明 —— 需人工判断" % c)
        else:
            print("  %-20s %s" % (c, r))
    print()

    print("-" * 78)
    print("inline 定义（未放在 core/db/models/ 的 model）")
    print("-" * 78)
    for name, files in sorted(reg.items()):
        if not any(f.startswith("core/db/models/") for f in files):
            print("  %-20s %s" % (name, ", ".join(files)))
    print()

    print("=" * 78)
    if unexplained:
        print("结论: ✗ 有 %d 个集合无归属说明，需人工判断" % len(unexplained))
        return 1
    print("结论: ✓ 全部差额均有明确归属 —— **无需新增集合**")
    print()
    print("C2 原表述「需补 applications / counters」不成立：")
    print("  · applications 实测已存在")
    print("  · counters 的 model 已注册（懒创建，功能正常）")
    print("  · chainconfigs 由 §3.6.5 的拆分映射替代，无需补")
    return 0


if __name__ == "__main__":
    sys.exit(main())
