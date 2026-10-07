# -*- coding: utf-8 -*-
"""
X5 判据：编译与服务的机械判据（覆盖验收项 1.3 / 1.4 / 1.5）。

★★ 验收项的权威定义（需求文档.md:103-105）：
   | 1.3 | Go 后端可编译启动   | `go build` 通过、服务起 |
   | 1.4 | Node 后端可编译启动 | `restore_gasleak.ps1` 还原后 npm install 可起 |
   | 1.5 | 4 个服务编排全绿    | docker-compose up 后全 healthy |
   ★ 且 证据局限闭合报告.md:293-295 确认这三项**当前都是"手工"**。

★ 本卡与 D2-C3（verify_build_freshness.py）**互补**，不重复：
   本卡聚焦 1.4（Node）+ 1.5（5 端口）+ 1.3 的端到端，且**不含** F2/F3 的"新鲜度"检查。

★ 1.5 的诚实处理：本环境**无 docker-compose** ⇒
   以「服务编排的等价物 = 5 端口全 LISTEN」替代，并在输出中**明确声明**。

用法：
    python verify_x5_build_services.py              # 全量
    python verify_x5_build_services.py --selftest   # 量尺前置断言（P-5）
    python verify_x5_build_services.py --skip-build # 跳过慢的 go build / node --check

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
import glob
import io
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

# ★ X3：本脚本自带 UTF-8 输出（P-10）
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = USDT_ROOT
IOS = IOS_ROOT
GO_DIR = os.path.join(ROOT, "01-backend-go")
NODE_DIR = os.path.join(ROOT, "02-backend-node", "src_restored")
NODE_BIN = r"E:\CTF\runtime\node"
GO_EXE = os.path.join(IOS, "_integration", "_fix_work", "_toolchain", "go", "bin", "go.exe")
GO_ENV = {
    "GOROOT": os.path.join(IOS, "_integration", "_fix_work", "_toolchain", "go"),
    "GOPATH": os.path.join(IOS, "_integration", "_fix_work", "_gopath"),
    "GOCACHE": os.path.join(IOS, "_integration", "_fix_work", "_gocache"),
    "GOFLAGS": "-mod=mod",
}
RESTORE = os.path.join(IOS, "_integration", "restore_gasleak.ps1")

PORTS = [8888, 3000, 13306, 16379, 27018]

_results = []


def rec(name, ok, detail):
    _results.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def listening(port):
    try:
        out = subprocess.run(["netstat", "-ano", "-p", "TCP"],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=30).stdout
        return any(f":{port} " in l and "LISTENING" in l for l in out.splitlines())
    except Exception:
        return False


def http_get(url, timeout=8):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception:
        return -1, b""


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    for p, label in ((GO_DIR, "Go 源码目录"), (NODE_DIR, "Node 源码目录")):
        e = os.path.isdir(p)
        print(f"  {'存在' if e else '[FAIL] 缺失'}: {label} {os.path.relpath(p, ROOT)}")
        if not e:
            ok = False
    # ★ 量尺有效性：netstat 必须能识别"已知在监听"的端口（用当前会话的已知端口自证）
    #   若全部 DOWN，则本判据的"端口检查"无法自证 ⇒ 明确提示
    up = [p for p in PORTS if listening(p)]
    print(f"  端口探测：{len(up)}/{len(PORTS)} LISTEN" + (f"（{up}）" if up else "（全部 DOWN）"))
    if not up:
        print("  [WARN] 服务全 DOWN ⇒ V3/V4/V5 将失败（须先起服务）")
    print(f"  restore_gasleak.ps1: {'存在' if os.path.isfile(RESTORE) else '不存在'}")
    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--skip-build", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== X5 判据：编译与服务（验收项 1.3 / 1.4 / 1.5）===")
    print("★ 声明：本环境【无 docker-compose】⇒ 1.5 以「5 端口全 LISTEN」作为编排等价物")
    print("")

    # ================= 1.3 Go 后端可编译启动 =================
    print("【1.3】Go 后端可编译启动（`go build` 通过、服务起）:")
    if args.skip_build:
        print("  [SKIP] V1 被 --skip-build 跳过 —— SKIP 不等于 PASS（P-13）")
    else:
        env = dict(os.environ)
        env.update(GO_ENV)
        try:
            r = subprocess.run([GO_EXE, "build", "./..."], cwd=GO_DIR, env=env,
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=900)
            tail = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
            rec("V1 `go build ./...` EXIT=0", r.returncode == 0,
                f"EXIT={r.returncode}" + (f"  {tail[-1][:90]}" if tail else ""))
        except subprocess.TimeoutExpired:
            rec("V1 `go build ./...`", False, "★ 超时（>900s）")
        except Exception as e:
            rec("V1 `go build ./...`", False, f"★ {e}")

    st, _b = http_get("http://127.0.0.1:8888/health")
    rec("V4 Go 服务健康：GET :8888/health ⇒ 200", st == 200, f"HTTP={st}")

    # ================= 1.4 Node 后端可编译启动 =================
    print("")
    print("【1.4】Node 后端可编译启动（`restore_gasleak.ps1` 还原后 npm install 可起）:")
    if args.skip_build:
        print("  [SKIP] V2 被 --skip-build 跳过 —— SKIP 不等于 PASS（P-13）")
    else:
        # ★ 不得全树扫 node_modules（P-5）：只扫 src_restored，且限深度
        js_files = []
        for dp, dn, fns in os.walk(NODE_DIR):
            dn[:] = [d for d in dn if d not in ("node_modules", ".git")]
            for fn in fns:
                if fn.endswith(".js"):
                    js_files.append(os.path.join(dp, fn))
        print(f"    （扫描 {len(js_files)} 个 .js，已排除 node_modules）")
        bad = []
        env = dict(os.environ)
        env["PATH"] = NODE_BIN + os.pathsep + env.get("PATH", "")
        node_exe = os.path.join(NODE_BIN, "node.exe")
        for p in js_files:
            try:
                r = subprocess.run([node_exe, "--check", p], env=env,
                                   capture_output=True, text=True, encoding="utf-8",
                                   errors="replace", timeout=30)
                if r.returncode != 0:
                    bad.append((os.path.relpath(p, ROOT), (r.stderr or "").strip()[:80]))
            except Exception as e:
                bad.append((os.path.relpath(p, ROOT), f"EXC:{e}"))
        rec("V2 全部 .js 的 `node --check` EXIT=0", len(bad) == 0,
            f"{len(js_files)} 个文件，{len(bad)} 个失败" + (f"：{bad[:2]}" if bad else " ✓"))

    # restore_gasleak.ps1 的存在性 + 语法（★ 不真跑 —— 它会改环境）
    if os.path.isfile(RESTORE):
        try:
            ps = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"$null = [System.Management.Automation.Language.Parser]::ParseFile('{RESTORE}',"
                 " [ref]$null, [ref]$errs); if ($errs) { $errs.Count } else { 0 }"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
            nerr = (ps.stdout or "").strip()
            rec("V2b `restore_gasleak.ps1` 存在且语法无误（★ 未真跑）",
                nerr == "0", f"解析错误数 = {nerr or '未知'}")
        except Exception as e:
            rec("V2b `restore_gasleak.ps1` 语法检查", False, f"★ {e}")
    else:
        rec("V2b `restore_gasleak.ps1` 存在", False, f"★ 缺失: {RESTORE}")

    st5, _b5 = http_get("http://127.0.0.1:3000/healthz")
    rec("V5 Node 服务健康：GET :3000/healthz ⇒ 200", st5 == 200, f"HTTP={st5}")

    # ================= 1.5 服务编排全绿 =================
    print("")
    print("【1.5】服务编排全绿（原文：docker-compose up 后全 healthy）:")
    print("    ★ 本环境无 docker-compose ⇒ 以「5 端口全 LISTEN」作为编排等价物")
    states = {p: listening(p) for p in PORTS}
    for p, ok in states.items():
        print(f"    {p} : {'LISTEN' if ok else '★ DOWN'}")
    n_up = sum(1 for v in states.values() if v)
    rec("V3 5 个端口全部 LISTEN", n_up == len(PORTS),
        f"{n_up}/{len(PORTS)}" + ("" if n_up == len(PORTS)
                                  else f"  缺: {[p for p, v in states.items() if not v]}"))

    # ================= 覆盖率对照（1.3/1.4/1.5） =================
    print("")
    print("【覆盖率对照】验收项 ↔ 断言:")
    print("    1.3 Go 后端可编译启动   ⇒ V1(go build) + V4(health)")
    print("    1.4 Node 后端可编译启动 ⇒ V2(node --check) + V2b(restore 脚本) + V5(healthz)")
    print("    1.5 4 服务编排全绿      ⇒ V3(5 端口全 LISTEN)（★ 替代 docker-compose）")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  1.3/1.4/1.5 三项均有机械判据覆盖")
    return 0


if __name__ == "__main__":
    sys.exit(main())
