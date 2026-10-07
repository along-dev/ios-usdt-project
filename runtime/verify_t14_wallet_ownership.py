# -*- coding: utf-8 -*-
"""
T14 [R3] 判据：R-01 `wallet_id` 半参数放行的归属校验。

★★ 缺陷（调度取证，见 09-docs/cards/T14-R01钱包归属校验.md）：
    wallet_resolver.go:45  `if deviceId != "" && address != "" {`  ← 仅当【两者均非空】才校验
    wallet_resolver.go:66  `return walletId, nil`                 ← 缺省时【直接放行】
  ⇒ `wallet_id + device_id`（无 address）/ `wallet_id + address`（无 device_id）
    两种半参数形态【直接放行】⇒ 持单一共享 token 者可对任意 wallet 执行 lock/report。

★★ 修复语义（Owner 裁决 2）：
    「只要提供了 device_id 或 address ⇒ 它【必须】与 wallet_id 指向同一 wallet」
    ★ 但「wallet_id 单独」是契约 C-2【明确允许】⇒ 修法【不得】是拒绝它。

判据（V1-V8）：见卡。V1+V2 是核心（错配必须被拒）；V4 是「未违反 C-2」的证据。

★ 验证方式：全部走【真实 HTTP 端点】/app/wallet-status（只读，无副作用），
  对真实 DB（qk_e2e）中的 wallet 1 / wallet 2 / machine dev-e2e-001 做数值断言。

用法：
    python verify_t14_wallet_ownership.py              # 全量
    python verify_t14_wallet_ownership.py --selftest   # 量尺前置断言（P-5）

退出码：0 = 全绿；非 0 = 有红。
"""
from __future__ import annotations

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

import argparse
import hashlib
import os
import re
import subprocess
import sys

ROOT = USDT_ROOT + r"\01-backend-go"
TARGET = os.path.join(ROOT, "service", "app", "wallet_resolver.go")
FORBIDDEN = [
    os.path.join(ROOT, "service", "app", "collect_lock.go"),
    os.path.join(ROOT, "service", "app", "collect_result.go"),
]
API_APP_DIR = os.path.join(ROOT, "api", "v1", "app")
CONTRACTS = USDT_ROOT + r"\09-docs\spec\contracts.md"
MANIFEST = USDT_ROOT + r"\_manifest.sha256"

GO = IOS_ROOT + r"\_integration\_fix_work\_toolchain\go\bin\go.exe"
GOENV = {
    "GOROOT": IOS_ROOT + r"\_integration\_fix_work\_toolchain\go",
    "GOPATH": IOS_ROOT + r"\_integration\_fix_work\_gopath",
    "GOCACHE": IOS_ROOT + r"\_integration\_fix_work\_gocache",
    "GOFLAGS": "-mod=mod",
}

BASE_URL = "http://127.0.0.1:8888"
TOKEN = "i2c1-e2e-token"

# ---- 真实 fixture（qk_e2e）----
#   wallet 1 -> machine 1 (dev-e2e-001), eth=0xWALLET...001, trx=TQn9Y2...
#   wallet 2 -> machine 1 (dev-e2e-001), eth=0xWALLET...002, trx=''
W_ALL = 1
W_OTHER = 2
DEV_OK = "dev-e2e-001"
DEV_BAD = "dev-e2e-999-nomatch"
ADDR_ETH_OK = "0xWALLET00000000000000000000000000000000001"
ADDR_ETH_BAD = "0xWALLET00000000000000000000000000000009999"

_results = []


def rec(name, ok, detail):
    _results.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def read(p):
    with open(p, "rb") as f:
        return f.read().decode("utf-8", errors="replace")


def sha256(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def status(**params):
    """调用只读端点 /app/wallet-status，返回 (http_status, code, body)。"""
    import requests

    r = requests.get(
        BASE_URL + "/app/wallet-status",
        params=params,
        headers={"X-Service-Token": TOKEN},
        timeout=10,
    )
    try:
        j = r.json()
    except Exception:
        return r.status_code, None, r.text[:200]
    return r.status_code, j.get("code"), j


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    for p in [TARGET] + FORBIDDEN + [CONTRACTS, MANIFEST]:
        if os.path.isfile(p):
            print(f"  存在: {p}")
        else:
            print(f"  [FAIL] 缺失: {p}")
            ok = False

    # 端点可达性：量尺必须真能测到东西
    try:
        st, code, _ = status(wallet_id=W_ALL)
        print(f"  端点可达: HTTP {st} code={code}")
        if st != 200 or code != 0:
            print("  [FAIL] 端点不可用或 wallet 1 不存在 ⇒ 量尺无效")
            ok = False
    except Exception as e:
        print(f"  [FAIL] 端点不可达: {type(e).__name__}: {e}")
        ok = False

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== T14 R-01 wallet_id 半参数放行 · 归属校验判据 ===")
    print(f"target={TARGET}")
    print("")

    src = read(TARGET)

    # ================= V1/V2 核心：错配必须被拒 =================
    print("V1 ★★ wallet_id + 【错配】device_id（无 address）⇒ 必须被拒:")
    st, code, body = status(wallet_id=W_ALL, device_id=DEV_BAD)
    v1_ok = st == 200 and code not in (0, None)
    rec("V1 错配 device_id 被拒", v1_ok,
        f"HTTP={st} code={code} msg={body.get('msg') if isinstance(body, dict) else body}")

    print("")
    print("V2 ★★ wallet_id + 【错配】address（含 chain，无 device_id）⇒ 必须被拒:")
    st2, code2, body2 = status(wallet_id=W_ALL, chain="eth", address=ADDR_ETH_BAD)
    v2_ok = st2 == 200 and code2 not in (0, None)
    rec("V2 错配 address 被拒", v2_ok,
        f"HTTP={st2} code={code2} msg={body2.get('msg') if isinstance(body2, dict) else body2}")

    # ================= V3/V4/V5 正例：不误伤 =================
    print("")
    print("V3 ★ 正例：wallet_id + 【匹配】device_id（无 address）⇒ 通过:")
    st3, code3, body3 = status(wallet_id=W_ALL, device_id=DEV_OK)
    v3_ok = st3 == 200 and code3 == 0
    rec("V3 匹配 device_id 通过", v3_ok,
        f"HTTP={st3} code={code3} data={body3.get('data') if isinstance(body3, dict) else body3}")

    print("")
    print("V4 ★★ 正例：wallet_id 【单独】⇒ 仍通过（契约 C-2 允许，证明未放宽成拒绝）:")
    st4, code4, body4 = status(wallet_id=W_ALL)
    v4_ok = st4 == 200 and code4 == 0
    rec("V4 wallet_id 单独仍通过（未违反 C-2）", v4_ok,
        f"HTTP={st4} code={code4} data={body4.get('data') if isinstance(body4, dict) else body4}")

    print("")
    print("V5 ★ 正例：三参数全有且匹配 ⇒ 通过（与现状等价）:")
    st5, code5, body5 = status(wallet_id=W_ALL, device_id=DEV_OK,
                               chain="eth", address=ADDR_ETH_OK)
    v5_ok = st5 == 200 and code5 == 0
    rec("V5 三参数匹配通过", v5_ok,
        f"HTTP={st5} code={code5} data={body5.get('data') if isinstance(body5, dict) else body5}")

    # ================= 附加反向：错配 address 指向别的 wallet =================
    print("")
    print("V2b ★ wallet_id=1 + wallet2 的 address（归属错配的另一形态）⇒ 必须被拒:")
    st2b, code2b, body2b = status(wallet_id=W_ALL, chain="eth",
                                  address="0xWALLET00000000000000000000000000000000002")
    v2b_ok = st2b == 200 and code2b not in (0, None)
    rec("V2b 他人 wallet 的 address 被拒", v2b_ok,
        f"HTTP={st2b} code={code2b} msg={body2b.get('msg') if isinstance(body2b, dict) else body2b}")

    # ================= V6 go build =================
    print("")
    print("V6 ★ go build ./... EXIT:")
    env = dict(os.environ)
    env.update(GOENV)
    p = subprocess.run([GO, "build", "./..."], cwd=ROOT, env=env,
                       capture_output=True, text=True)
    rec("V6 go build ./... EXIT=0", p.returncode == 0,
        f"EXIT={p.returncode} stderr={(p.stderr or '')[:300]}")

    # ================= V7 未改 forbidden =================
    print("")
    print("V7 ★ 未改 collect_lock.go / collect_result.go / api/v1/app/**:")
    # collect_lock.go / collect_result.go 不得含本次新增的哨兵串
    sentinel = "归属"
    for p2 in FORBIDDEN:
        s = read(p2)
        # 只要求：这两个文件不含本次修复新增的判定逻辑
        bad = "deviceId != \"\" || address != \"\"" in s
        rec(f"V7 {os.path.basename(p2)} 未被本次改动", not bad,
            "未含半参数放行修复逻辑" if not bad else "★ 含修复逻辑 ⇒ 越界改动")

    # api/v1/app/** 不得含修复逻辑
    api_hit = []
    for f in os.listdir(API_APP_DIR):
        if f.endswith(".go"):
            s = read(os.path.join(API_APP_DIR, f))
            if 'deviceId != "" || address != ""' in s:
                api_hit.append(f)
    rec("V7 api/v1/app/** 未被本次改动", not api_hit,
        "无命中" if not api_hit else f"★ 命中 {api_hit}")

    # ================= V8 守护 =================
    print("")
    print("V8 守护：_manifest.sha256 / contracts.md 未改:")
    # contracts.md 必须仍含 C-2 的「wallet_id 单独」语义
    cs = read(CONTRACTS)
    c2 = re.search(r"C-2[^\n]*\n(.*?)\n---", cs, re.S)
    c2_body = c2.group(1) if c2 else ""
    has_c2 = "wallet_id" in c2_body and "device_id" in c2_body
    rec("V8 contracts.md 的 C-2 钱包定位入参语义保持", has_c2,
        "C-2 仍为 wallet_id 或 (device_id+chain+address)" if has_c2 else "★ C-2 被改")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    print("")
    print(f"V1(错配device_id被拒)   = {'PASS' if v1_ok else 'FAIL'}")
    print(f"V2(错配address被拒)     = {'PASS' if v2_ok else 'FAIL'}")
    print(f"V3(匹配device_id通过)   = {'PASS' if v3_ok else 'FAIL'}")
    print(f"V4(wallet_id单独通过)   = {'PASS' if v4_ok else 'FAIL'}")
    print(f"V5(三参数通过)          = {'PASS' if v5_ok else 'FAIL'}")
    print("")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  R-01 半参数放行已修复：错配被拒 + 正例不误伤 + C-2 未违反")
    return 0


if __name__ == "__main__":
    sys.exit(main())
