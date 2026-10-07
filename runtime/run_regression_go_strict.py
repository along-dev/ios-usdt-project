# -*- coding: utf-8 -*-
"""T50/T54 置位点 —— 以【假绿族严格档】跑本仓 Go 测试（`DSH_REQUIRE_ISOLATED_DB=1`）。

★ 为什么需要它（`F-T47-3`）：`T47`/`T50` 给 `blockchain` 包里那些「前提缺失即 `t.Skip`」
   的测试加了**严格档开关**；但**给了开关没人按** ⇒ 默认路径仍「全 skip ⇒ 退出码 0」
   ⇒ **假绿在默认路径下依然存在**（在册 `E-359`/`E-360` 族「恒绿＝没检查」）。
   ⇒ 本脚本就是那个「**按它**」的人：门禁/CI 要判「全绿」时，**按它**跑。

★ 效果：置位后，`blockchain` 包里
   · `billing_test.go`（`WBE01A_TEST_DSN` 未设）
   · `t44_v1_test.go`（隔离库 `qk_e2e_test` 不可用）
   等「前提缺失」不再静默 `Skip`，而是 **`Fatal` ⇒ `go test` 退出码 ≠ 0**。

★ **谁在按它**（`T54`／`F-T50-1` 接线闭合）：**本仓的「Go 全绿」验收/复核动作**按它 ——
   见 `E:\\USDT项目\\07-db\\README.md` §「假绿族严格档（谁在跑全绿时按它）」。
   ⛔ **不按它 = 默认档 ⇒ 全 skip 仍退 0 ⇒ 假绿**。
★ **可机检的置位证据**：`--selftest`（★ 见下）—— 它对**同一个 DB-free 用例**跑
   **严格／默认 A/B**，断言「默认 0 ／ 严格 ≠0」，并打印 `PLACEMENT=OK`。
   ⇒ 谁质疑「开关有没有真接上」，跑它一次即可复核（退出码确定、可进任何门禁）。

用法：
    python run_regression_go_strict.py                 # 严格档跑 go test ./...
    python run_regression_go_strict.py ./blockchain/   # 只跑指定包
    python run_regression_go_strict.py --selftest      # ★ 置位自证（A/B）⇒ PLACEMENT=OK

★ 只置环境变量并转调 `go test`：不联网、不启停服务、不写库。
  ⛔ 不带本脚本时，行为**逐字不变**（默认档 = 老的 skip 语义）。
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import os
import subprocess
import sys

REPO_GO = USDT_ROOT + r"\01-backend-go"
# ★ 一律用 E:\ 真实路径（⛔ 不用 X:\ —— 那是 subst 会话级映射、重启即失效；本机在册 E-11/P-45）
FW = IOS_ROOT + r"\_integration\_fix_work"
GOROOT = IOS_ROOT + r"\_integration\_fix_work\_toolchain\go"
GOPATH = IOS_ROOT + r"\_integration\_fix_work\_gopath"
# ★ 用 go.exe 全路径：Windows 的 CreateProcess 不按 PATHEXT 补 `.exe` ⇒ 只写 "go" 会 WinError 2
GO_EXE = os.path.join(GOROOT, "bin", "go.exe")

# ★ 置位自证专用的 DB-free 用例：billing（无 WBE01A_TEST_DSN ⇒ 默认 SKIP／严格 Fatal）
#   ＋ T54 的白名单纯函数单测（零 DB 写，两档都 PASS）。
SELFTEST_PKGS = ["./blockchain/"]
SELFTEST_RUN = "TestAccumulateUsdtNum|TestT54_WhiteListGuard"


def _env(strict: bool) -> dict:
    env = dict(os.environ)
    if strict:
        env["DSH_REQUIRE_ISOLATED_DB"] = "1"  # ★ 置位：假绿族严格档
    else:
        env.pop("DSH_REQUIRE_ISOLATED_DB", None)  # 默认档：确保不残留
    env["GOROOT"] = GOROOT
    env["GOPATH"] = GOPATH
    env["PATH"] = os.path.join(GOROOT, "bin") + os.pathsep + env.get("PATH", "")
    # ★★ T54（`F-T50-3`）**自足**：原来只设 GOROOT/GOPATH ⇒ 仍依赖调用方的 `GOCACHE`/`GOFLAGS`。
    #   现在**显式给出确定值**（★ `setdefault` ⇒ 调用方仍可覆盖）⇒ 换一个干净 shell 也能复现同一结果。
    env.setdefault("GOCACHE", os.path.join(FW, "_gocache"))  # 项目内确定性构建缓存
    env.setdefault("GOFLAGS", "-mod=readonly")               # pin：只读模块解析（⛔ 不写 go.mod/go.sum）
    return env


def _go_test(env: dict, pkgs, run=None) -> int:
    cmd = [GO_EXE, "test", "-count=1"] + pkgs
    if run:
        cmd += ["-run", run]
    txt = "DSH_REQUIRE_ISOLATED_DB=%s ⇒ %s" % (env.get("DSH_REQUIRE_ISOLATED_DB", "(未设)"), " ".join(cmd))
    print("  " + txt, flush=True)
    return subprocess.call(cmd, cwd=REPO_GO, env=env)


def selftest() -> int:
    print("=== T54 置位自证（A/B：默认 vs 严格；DB-free 用例）===", flush=True)
    rc_default = _go_test(_env(False), SELFTEST_PKGS, SELFTEST_RUN)
    rc_strict = _go_test(_env(True), SELFTEST_PKGS, SELFTEST_RUN)
    print("  [A 默认档] EXIT=%d（期望 0；缺前置静默 SKIP）" % rc_default, flush=True)
    print("  [B 严格档] EXIT=%d（期望 ≠0；缺前置 Fatal 响亮红）" % rc_strict, flush=True)
    ok = (rc_default == 0) and (rc_strict != 0)
    print("PLACEMENT=%s" % ("OK" if ok else "BAD"), flush=True)
    return 0 if ok else 2


def main():
    if "--selftest" in sys.argv:
        return selftest()
    pkgs = sys.argv[1:] or ["./..."]
    print("★ T50 严格档：DSH_REQUIRE_ISOLATED_DB=1", flush=True)
    return _go_test(_env(True), pkgs)


if __name__ == "__main__":
    sys.exit(main())
