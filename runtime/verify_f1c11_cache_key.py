# -*- coding: utf-8 -*-
"""
F1-C11 判据：载荷配置缓存键必须含设备维度。

★ 核心：**不清缓存**，逐 UA 请求，断言不同链必须得到不同响应。

用法：
    python verify_f1c11_cache_key.py              # 全量
    python verify_f1c11_cache_key.py --selftest   # 量尺前置断言（P-5）

退出码：0 = 全绿；非 0 = 有红。
"""
from __future__ import annotations

# ★ X3：本脚本【自带】UTF-8 输出，不依赖调用方设置 PYTHONIOENCODING（P-10）
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
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
import json
import subprocess
import sys
import urllib.error
import urllib.request

API = "http://127.0.0.1:3000"
ENDPOINT = "/details/show.html"
RCLI = [IOS_ROOT + r"\_integration\_fix_work\_toolchain\redis\redis-cli.exe"]

_results = []


def rec(name, ok, detail):
    _results.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def get(ua, timeout=20):
    req = urllib.request.Request(API + ENDPOINT, method="GET")
    req.add_header("User-Agent", ua)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return r.status, (r.headers.get("Content-Type") or ""), raw
    except urllib.error.HTTPError as e:
        return e.code, ((e.headers.get("Content-Type") or "") if e.headers else ""), e.read()
    except Exception as e:
        return -1, "", f"EXC:{e}".encode()


def flush():
    try:
        out = subprocess.run(RCLI + ["-h", "127.0.0.1", "-p", "16379", "KEYS", "payload_config:*"],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace").stdout.strip()
        for k in out.splitlines():
            if k.strip():
                subprocess.run(RCLI + ["-h", "127.0.0.1", "-p", "16379", "DEL", k.strip()],
                               capture_output=True)
    except Exception:
        pass


def cache_keys():
    try:
        out = subprocess.run(RCLI + ["-h", "127.0.0.1", "-p", "16379", "KEYS", "payload_config:*"],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace").stdout.strip()
        return [k for k in out.splitlines() if k.strip()]
    except Exception:
        return []


def ua_for(major, minor):
    return (f"Mozilla/5.0 (iPhone; CPU iPhone OS {major}_{minor} like Mac OS X) "
            f"AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")


UA_CORUNA = ua_for(16, 5)
UA_DARK = ua_for(18, 4)
UA_BLANK = ua_for(17, 5)
UA_CORUNA2 = ua_for(16, 6)   # 同链不同小版本（用于 C3 防碎片化）
UA_WIN = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def md5(b):
    return hashlib.md5(b).hexdigest()[:12]


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True

    st, ct, raw = get(UA_CORUNA)
    if st == 200:
        print(f"  Node 就绪: {ENDPOINT} 200 ({len(raw)}B)")
    else:
        print(f"  [FAIL] Node 不可达 ({st})")
        ok = False

    # ★ 量尺有效性：清缓存后三路必须可区分（若这都不成立，判据无意义）
    flush()
    _s, _c, r1 = get(UA_CORUNA)
    flush()
    _s, _c, r2 = get(UA_DARK)
    flush()
    _s, _c, r3 = get(UA_BLANK)
    if not (r1 == r2 == r3):
        print(f"  量尺有效：清缓存后三路可区分（{len(r1)}/{len(r2)}/{len(r3)}B）")
    else:
        print("  [FAIL] 清缓存后三路仍相同 —— 无法区分'缓存缺陷'与'路由缺陷'")
        ok = False

    # ★ 量尺有效性：缓存确实生效（否则"不清缓存"这个前提不成立）
    flush()
    get(UA_CORUNA)
    k1 = cache_keys()
    if k1:
        print(f"  缓存确实写入: {k1}")
    else:
        print("  [WARN] 缓存未写入（可能 unsupported 不缓存）—— C1 的前提需复核")
        # 用 coruna（会写缓存）再试一次
        flush()
        get(UA_CORUNA)
        k2 = cache_keys()
        print(f"    重试后: {k2}")

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== F1-C11 缓存键设备维度判据（不清缓存）===")
    print(f"端点: {API}{ENDPOINT}")
    print("")

    # ---- C1: 不清缓存，三路必须互不相同 ----
    print("C1 不清缓存，依次请求三路（核心）:")
    flush()
    s1, c1, r1 = get(UA_CORUNA)
    s2, c2, r2 = get(UA_DARK)
    s3, c3, r3 = get(UA_BLANK)
    print(f"    iOS16.5 -> {len(r1)}B md5={md5(r1)} ct={c1}")
    print(f"    iOS18.4 -> {len(r2)}B md5={md5(r2)} ct={c2}")
    print(f"    iOS17.5 -> {len(r3)}B md5={md5(r3)} ct={c3}")
    print(f"    缓存键: {cache_keys()}")
    rec("C1 三路响应互不相同（缓存未串味）",
        r1 != r2 and r2 != r3 and r1 != r3,
        f"md5 = {md5(r1)} / {md5(r2)} / {md5(r3)}"
        + ("" if (r1 != r2 and r2 != r3) else "  ← 存在相同，缓存串味"))
    print("")

    # ---- C2: 顺序污染反向 —— Windows 先请求，iOS 仍须拿到载荷 ----
    print("C2 顺序污染反向（Windows 先请求，iOS 仍须拿到载荷）:")
    flush()
    sw, cw, rw = get(UA_WIN)
    s1b, c1b, r1b = get(UA_CORUNA)
    print(f"    Windows  -> {len(rw)}B ct={cw}")
    print(f"    然后 iOS16.5 -> {len(r1b)}B ct={c1b}")
    is_payload = r1b[:6].hex() == "377abcaf271c"
    rec("C2 unsupported 请求不污染后续设备", is_payload,
        f"iOS16.5 拿到 {'载荷(7z)' if is_payload else '非载荷: ' + r1b[:60].decode('utf-8','replace')}")
    print("")

    # ---- C3: 同链设备应共享缓存（防碎片化）----
    print("C3 同链设备（iOS 16.5 vs 16.6）应共享缓存（防碎片化）:")
    flush()
    _sa, _ca, ra = get(UA_CORUNA)
    _sb, _cb, rb = get(UA_CORUNA2)
    keys_after = cache_keys()
    rec("C3 同链不同小版本响应相同", ra == rb,
        f"md5 = {md5(ra)} vs {md5(rb)}")
    rec("C3 缓存键未因同链碎片化（键数应很少）", len(keys_after) <= 2,
        f"键数={len(keys_after)}: {keys_after}")
    print("")

    # ---- C4: 清缓存后与 I1-C3 结果一致 ----
    print("C4 清缓存后三路形状正确:")
    flush()
    _s, cA, rA = get(UA_CORUNA)
    flush()
    _s, cB, rB = get(UA_DARK)
    flush()
    _s, cC, rC = get(UA_BLANK)
    rec("C4 coruna 为 7z 载荷", rA[:6].hex() == "377abcaf271c", f"{len(rA)}B {cA}")
    rec("C4 darksword 为 7z 载荷", rB[:6].hex() == "377abcaf271c", f"{len(rB)}B {cB}")
    rec("C4 空白区为显式 unsupported", "json" in (cC or "") and b"unsupported" in rC,
        f"{len(rC)}B body={rC.decode('utf-8','replace')[:60]}")
    print("")

    # ---- C5: invalidateConfigCache 的 KEYS 前缀仍能匹配 ----
    print("C5 invalidateConfigCache 兼容性（前缀必须仍是 payload_config:）:")
    flush()
    get(UA_CORUNA)
    keys5 = cache_keys()
    ok5 = len(keys5) > 0 and all(k.startswith("payload_config:") for k in keys5)
    rec("C5 新键仍以 payload_config: 开头（KEYS 通配可清）", ok5,
        f"键={keys5}")
    # 实证：通配删除确实能清空
    flush()
    after = cache_keys()
    rec("C5 通配删除后键已清空", len(after) == 0, f"剩余={after}")
    print("")

    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  缓存键已隔离设备维度，且同链不碎片化、可被通配清除")
    return 0


if __name__ == "__main__":
    sys.exit(main())
