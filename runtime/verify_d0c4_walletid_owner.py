# -*- coding: utf-8 -*-
"""
D0-C4 判据：ResolveWalletId 的 wallet_id 直传分支须做交叉一致性校验。

★★ 缺陷（已由调度实测确证，2026-09-29）：
   wallet_resolver.go:36-38
       if walletId > 0 { return walletId, nil }      ← ★ 直取，无任何校验
   而反查路径(:48-55)有 `machine.device_id = ?` 约束 ⇒ 两条路径严格性不一致。

   4 个调用点【全部】同时持有 wallet_id 与 device_id+address：
     service/app/collect_lock.go:54 / :87
     service/app/collect_result.go:62
     api/v1/app/wallet_status.go:41-42
   ⇒ 当二者【同时提供】时应校验它们指向同一 wallet。

   危害：服务间是【单一共享 token】（X-Service-Token），非按调用方区分
   ⇒ 持 token 者可对【任意 wallet_id】执行 lock / release / report。

修复口径（Owner 已裁 (a1)）：wallet_id 与 device_id+address 同时提供时，
   必须校验三者指向同一 wallet；不一致则【拒绝】。

用法：
    python verify_d0c4_walletid_owner.py              # 全量
    python verify_d0c4_walletid_owner.py --selftest   # 量尺前置断言（P-5）

退出码：0 = 全绿；非 0 = 有红。
"""
from __future__ import annotations

# ★ X3：本脚本【自带】UTF-8 输出，不依赖调用方设置 PYTHONIOENCODING（P-10）
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
import sys

ROOT = USDT_ROOT + r"\01-backend-go"
TARGET = os.path.join(ROOT, "service", "app", "wallet_resolver.go")
CALLERS = [
    os.path.join(ROOT, "service", "app", "collect_lock.go"),
    os.path.join(ROOT, "service", "app", "collect_result.go"),
    os.path.join(ROOT, "api", "v1", "app", "wallet_status.go"),
]

_results = []


def rec(name, ok, detail):
    _results.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def read(p):
    return open(p, encoding="utf-8", errors="replace").read()


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    for p in [TARGET] + CALLERS:
        if os.path.isfile(p):
            print(f"  存在: {os.path.basename(p)} ({os.path.getsize(p)} B)")
        else:
            print(f"  [FAIL] 缺失: {p}")
            ok = False

    src = read(TARGET)
    # 前提：当前 walletId>0 分支必须【确实】是直取（否则本判据无意义）
    if re.search(r"if\s+walletId\s*>\s*0\s*\{\s*\n\s*return\s+walletId\s*,\s*nil", src):
        print("  前提成立：walletId>0 分支当前为直取")
    else:
        print("  [WARN] 未匹配到直取形态 —— 可能已修，或写法不同（须人工确认）")

    # 量尺有效性：模式须能区分「直取」与「带校验」
    direct = "if walletId > 0 {\n\t\treturn walletId, nil\n\t}"
    guarded = ("if walletId > 0 {\n\t\tif deviceId != \"\" && address != \"\" {\n"
               "\t\t\t// check\n\t\t}\n\t\treturn walletId, nil\n\t}")
    if re.search(r"return\s+walletId\s*,\s*nil", direct) and \
       re.search(r"deviceId\s*!=\s*\"\"", guarded):
        print("  模式有效：可区分直取与带校验形态")
    else:
        print("  [FAIL] 模式失效")
        ok = False

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== D0-C4 ResolveWalletId 交叉一致性校验判据 ===")
    print("")

    src = read(TARGET)

    # ---- C1: walletId>0 分支必须存在交叉校验（而非无条件直取）----
    print("C1 walletId>0 分支须做交叉一致性校验:")
    # 提取 walletId>0 分支的主体
    m = re.search(r"if\s+walletId\s*>\s*0\s*\{(.*?)\n\t\}", src, re.S)
    body = m.group(1) if m else ""
    has_check = bool(re.search(r"deviceId", body) and re.search(r"address", body))
    rec("C1 分支内引用了 deviceId 与 address（即做了交叉校验）", has_check,
        "已引用" if has_check else "★ 未引用 ⇒ 仍是无条件直取（缺陷）")
    if body:
        print("    分支体前 6 行:")
        for l in body.strip().splitlines()[:6]:
            print(f"      {l.strip()}")

    # ---- C2: 必须存在「不一致 ⇒ 拒绝」的出口 ----
    print("")
    print("C2 须存在「不一致 ⇒ 拒绝」:")
    # 在同一分支内应出现 return 0, err / return 0, fmt.Errorf
    rejects = re.findall(r"return\s+0\s*,\s*(?:errors\.New|fmt\.Errorf)", body or "")
    rec("C2 分支内有拒绝出口（return 0, err）", len(rejects) > 0,
        f"命中 {len(rejects)} 处" + ("" if rejects else "  ★ 无不一致拒绝 ⇒ 校验不完整"))

    # ---- C3: 仍须保留「只传 wallet_id」的兼容（防改过头）----
    print("")
    print("C3 防改过头：仅传 wallet_id 时必须仍能通过（兼容既有语义）:")
    # 校验应【有条件】——只在 deviceId/address 都非空时才比对
    cond = bool(re.search(r"deviceId\s*!=\s*\"\"\s*&&\s*address\s*!=\s*\"\"", src) or
                re.search(r"deviceId\s*!=\s*\"\"\s*&&\s*address\s*!=\s*\"\"", src))
    rec("C3 校验以「deviceId 与 address 均非空」为前提", cond,
        "已加前提（兼容只传 wallet_id）" if cond else "★ 无条件校验会破坏既有语义")

    # ---- C4: 反查路径（device_id+address 反查）不得被破坏 ----
    print("")
    print("C4 反查路径须保持可用:")
    rec("C4 仍含 machine.device_id 反查", "machine.device_id = ?" in src or "machine.device_id=?" in src,
        "OK" if "machine.device_id" in src else "★ 反查被破坏")

    # ---- C5: 4 个调用点仍传 device_id 与 address ----
    print("")
    print("C5 调用点须仍传 device_id 与 address:")
    for p in CALLERS:
        if not os.path.isfile(p):
            continue
        s = read(p)
        n = len(re.findall(r"ResolveWalletId\(", s))
        has_dev = "DeviceId" in s or 'device_id' in s
        has_addr = "Address" in s or 'address' in s
        rec(f"C5 {os.path.basename(p)}（{n} 处调用）传 device_id/address",
            has_dev and has_addr, f"deviceId={has_dev} address={has_addr}")

    # ---- C6: 不得改 DTO（契约 C-2）----
    print("")
    print("C6 防越界：不得改 DTO（契约 C-2 只读）:")
    common = os.path.join(ROOT, "model", "common.go")
    if os.path.isfile(common):
        s = read(common)
        # ReqCollectResult 字段应仍为原来 4+ 个（不含新增的归属字段）
        m2 = re.search(r"type ReqCollectResult struct\s*\{(.*?)\n\}", s, re.S)
        fields = re.findall(r"^\s*(\w+)\s+", m2.group(1), re.M) if m2 else []
        no_new = not any(f.lower() in ("machineid", "agentid", "customid", "callerid")
                         for f in fields)
        rec("C6 DTO 未新增归属字段（未触碰契约 C-2）", no_new, f"字段={fields}")
    else:
        rec("C6 DTO 未新增归属字段", False, "common.go 不存在")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  wallet_id 直传已做交叉一致性校验，且兼容与反查未破坏")
    return 0


if __name__ == "__main__":
    sys.exit(main())
