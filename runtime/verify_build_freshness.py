# -*- coding: utf-8 -*-
"""
D2-C3 判据：构建-源码一致性门禁。

★★ 本卡源于 D0-C4 收口时的实证坑：
   静态判据全绿 + go build/vet EXIT=0，**但真 HTTP 断言失败**
   —— 因为 8888 跑的是【2 天前的旧二进制】（源码 09-30 01:04，二进制 09-28 22:05）。
   重编重启后 R1–R6 才全符合。
   ⇒ 本判据把"跑的是新代码"这一前提变成【机械门禁】。

用法：
    python verify_build_freshness.py              # 全量
    python verify_build_freshness.py --selftest   # 量尺前置断言（P-5）
    python verify_build_freshness.py --skip-build # 跳过 F4（go build 慢）

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
import base64
import glob
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = USDT_ROOT
GO_DIR = os.path.join(ROOT, "01-backend-go")
GO_EXE = IOS_ROOT + r"\_integration\_fix_work\_toolchain\go\bin\go.exe"
GO_ENV = {
    "GOROOT": IOS_ROOT + r"\_integration\_fix_work\_toolchain\go",
    "GOPATH": IOS_ROOT + r"\_integration\_fix_work\_gopath",
    "GOCACHE": IOS_ROOT + r"\_integration\_fix_work\_gocache",
    "GOFLAGS": "-mod=mod",
}
API = "http://127.0.0.1:8888"

_results = []


def rec(name, ok, detail):
    _results.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def ts(t):
    return time.strftime("%m-%d %H:%M:%S", time.localtime(t))


def http_get(path, timeout=8, headers=None):
    req = urllib.request.Request(API + path, method="GET")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception:
        return -1, b""


# ★ /app/* 端点需【服务间 token】（契约 C-2：header `X-Service-Token`）
SERVICE_TOKEN = os.environ.get("QIANKE_SERVICE_TOKEN", "i2c1-e2e-token")
SERVICE_HDR = {"X-Service-Token": SERVICE_TOKEN}


def find_listener_pid(port):
    """用 netstat 找监听端口的 PID（不依赖 psutil）。"""
    try:
        out = subprocess.run(["netstat", "-ano", "-p", "TCP"],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=30).stdout
        for line in out.splitlines():
            if f":{port} " in line and "LISTENING" in line:
                parts = line.split()
                return int(parts[-1])
    except Exception:
        pass
    return None


def proc_info(pid):
    """返回 (exe_path, start_time)。用 PowerShell 取（不依赖 psutil）。

    ★★ T69（假红修复）：旧法把**含中文的路径**经 `ConvertTo-Json` 直接写到**控制台**，
       而本机控制台编码是 GBK（cp936）⇒ `漏洞` 被毁成 `©??`（实测 **2026-10-05**：
       `E:\\ios©??\\_integration\\...`）⇒ `os.path.isfile()` 判假 ⇒ `F2` **根本没算**、
       `F3` 连带 `SKIP` ⇒ **本机任何 Go 卡收口恒 `RESULT=RED`**（**恒红＝没有检查**）。
       ⇒ 现改为：路径在 PowerShell 侧**先取 UTF-8 字节、再 Base64**（**纯 ASCII**）送出
         ⇒ **控制台编码完全不经手**；Python 侧 `b64decode().decode('utf-8')` 还原。
       ★ 这是「显式 UTF-8 读」的<ins>免疫</ins>实现 —— 不依赖 `[Console]::OutputEncoding`，
         也不赌"cp936 还是 utf-8"猜得对。"""
    ps = (
        f"$p = Get-Process -Id {pid} -ErrorAction SilentlyContinue; "
        "if ($p) { "
        "  $pb = $null; "
        "  if ($p.Path) { $pb = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($p.Path)) } "
        "  $st = $null; "
        "  if ($p.StartTime) { $st = $p.StartTime.ToString('o') } "
        "  $o = [ordered]@{ path_b64 = $pb; start = $st }; "
        "  $o | ConvertTo-Json -Compress "
        "}"
    )
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=30).stdout.strip()
        if out:
            j = json.loads(out)
            pb = j.get("path_b64")
            path = base64.b64decode(pb).decode("utf-8", "replace") if pb else j.get("path")
            return path, j.get("start")
    except Exception:
        pass
    return None, None


def newest_go_mtime():
    """返回 (path, mtime) 最新的 .go 文件。"""
    newest = (None, 0.0)
    n = 0
    for dp, dn, fns in os.walk(GO_DIR):
        dn[:] = [d for d in dn if d not in ("node_modules", ".git")]
        for fn in fns:
            if fn.endswith(".go"):
                p = os.path.join(dp, fn)
                try:
                    m = os.path.getmtime(p)
                except OSError:
                    continue
                n += 1
                if m > newest[1]:
                    newest = (p, m)
    return newest, n


def parse_iso(s):
    """解析 PowerShell 的 ISO 时间串。"""
    if not s:
        return None
    try:
        s2 = s.replace("Z", "+00:00")
        # 去掉过多的纳秒
        import re
        s2 = re.sub(r"(\.\d{6})\d+", r"\1", s2)
        from datetime import datetime
        return datetime.fromisoformat(s2).timestamp()
    except Exception:
        return None


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True

    # 1) Go 源码目录存在且含 .go
    newest, n = newest_go_mtime()
    if n > 0:
        print(f"  扫描到 {n} 个 .go 文件；最新: {os.path.relpath(newest[0], ROOT)} @ {ts(newest[1])}")
    else:
        print("  [FAIL] 未扫到任何 .go ⇒ 量尺可能坏了")
        ok = False

    # 2) 端口扫描有效（能找到监听 PID）
    pid = find_listener_pid(8888)
    if pid:
        print(f"  8888 监听 PID = {pid}")
    else:
        print("  [WARN] 8888 无监听进程 —— F1/F3 将失败（服务未起）")

    # 3) 进程信息可读
    if pid:
        path, start = proc_info(pid)
        if path:
            print(f"    进程路径 = {path}")
            print(f"    启动时间 = {start}")
        else:
            print("  [WARN] 进程路径/启动时间不可读 ⇒ F3 将 SKIP")

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--skip-build", action="store_true", help="跳过 F4（go build 慢）")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== D2-C3 构建-源码一致性门禁 ===")
    print("")

    # ---- F1: 8888 有监听进程 ----
    print("F1 服务进程:")
    pid = find_listener_pid(8888)
    rec("F1 8888 有监听进程", bool(pid), f"PID={pid}" if pid else "★ 无监听进程")

    exe_path, exe_start = (None, None)
    if pid:
        exe_path, exe_start = proc_info(pid)
        rec("F1 进程可执行路径可读", bool(exe_path), exe_path or "★ 不可读")

    # ---- F2: 二进制 mtime >= 源码最大 mtime ----
    print("")
    print("F2 ★ 二进制不早于源码（核心）:")
    newest, n = newest_go_mtime()
    bin_mtime = None
    if exe_path and os.path.isfile(exe_path):
        bin_mtime = os.path.getmtime(exe_path)
        print(f"    二进制: {os.path.basename(exe_path)} @ {ts(bin_mtime)}")
        print(f"    最新源: {os.path.relpath(newest[0], ROOT)} @ {ts(newest[1])}")
        delta = bin_mtime - newest[1]
        rec("F2 二进制 mtime >= 源码最大 mtime", delta >= 0,
            f"差 {delta:+.1f}s" + ("" if delta >= 0 else "  ★ 源码比二进制新 ⇒ 需重编重启"))
    else:
        rec("F2 二进制不早于源码", False,
            "★ 无法取得二进制路径（进程信息不可读）")

    # ---- F3: 进程启动时间 >= 二进制 mtime ----
    print("")
    print("F3 ★ 进程加载的是当前二进制:")
    st = parse_iso(exe_start)
    if st and bin_mtime:
        d3 = st - bin_mtime
        rec("F3 进程启动 >= 二进制 mtime", d3 >= -2,  # 容 2s 误差
            f"启动 {ts(st)} vs 二进制 {ts(bin_mtime)}（差 {d3:+.1f}s）"
            + ("" if d3 >= -2 else "  ★ 跑的是旧加载"))
    else:
        print("  [SKIP] 启动时间或二进制 mtime 不可得 —— SKIP 不等于 PASS（P-13）")

    # ---- F4: go build ----
    print("")
    print("F4 可编译:")
    if args.skip_build:
        print("  [SKIP] 被 --skip-build 跳过 —— SKIP 不等于 PASS（P-13）")
    else:
        env = dict(os.environ)
        env.update(GO_ENV)
        try:
            r = subprocess.run([GO_EXE, "build", "./..."], cwd=GO_DIR, env=env,
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=900)
            tail = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
            rec("F4 go build ./... EXIT=0", r.returncode == 0,
                f"EXIT={r.returncode}" + (f"  {tail[-1][:100]}" if tail else ""))
        except subprocess.TimeoutExpired:
            rec("F4 go build", False, "★ 超时（>900s）")

    # ---- F5: 运行时探活 ----
    print("")
    print("F5 运行时探活:")
    st5, b5 = http_get("/health")
    rec("F5 GET /health => 200", st5 == 200, f"HTTP={st5} body={b5[:60]}")

    # ---- F6: 端到端否定断言（证明新校验生效）----
    #
    # ★★ 修正（2026-09-30，自查）：初版【未带 X-Service-Token】⇒ 得 401
    #    "invalid or missing X-Service-Token"，即【鉴权层】就拒了，
    #    根本没到业务校验 ⇒ 该断言证明不了"新校验生效"。
    #    ⇒ 必须带 service token（契约 C-2），才能触达业务层。
    print("")
    print("F6 ★ 端到端否定断言（新校验应生效）:")
    st6, b6 = http_get(
        "/app/wallet-status?wallet_id=999999&chain=tron&device_id=x&address=y",
        headers=SERVICE_HDR)
    body6 = b6.decode("utf-8", "replace")
    # 期望：HTTP 200（契约 C-2：/app/* 恒 200）+ 业务码非 0（被业务层拒绝）
    st6b, b6b = http_get("/app/wallet-status?wallet_id=999999&chain=tron&device_id=x&address=y")
    body6b = b6b.decode("utf-8", "replace")
    print(f"    （对照：不带 token => HTTP {st6b} {body6b[:90]}）")
    is_biz_fail = st6 == 200 and '"code":0' not in body6
    rec("F6 带 token 后 wallet_id=999999 => 业务码非 0（业务层拒绝）", is_biz_fail,
        f"HTTP={st6} body={body6[:140]}")
    rec("F6 对照：不带 token => 401（鉴权层拦在前）", st6b == 401,
        f"HTTP={st6b}（证明 token 是【触达业务层】的前提）")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  二进制不早于源码、进程已加载、可编译、服务活跃、新校验生效")
    return 0


if __name__ == "__main__":
    sys.exit(main())
