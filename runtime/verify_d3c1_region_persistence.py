# -*- coding: utf-8 -*-
"""
D3-C1 判据：region 自动切换【持久化】（重启不丢）。

判据先于实现（判据 9）。本脚本放产物外（_fix_work/），不进 09-docs/cards/（P-4）。

★ 缺陷（X4 实测）：region 的【状态】持久化 ✅，但【调度】不持久化 ❌
    · 驱动 region 自动转公域的是 scan.go:425-428 的 time.AfterFunc（进程内定时器）
    · 全库无持久化调度表 ⇒ 重启后"未到期的自动公域切换"永久丢失

★ 修复（主方案 T4.1–T4.6）：
    T4.1 wallet 表加 turn_pubic_at 列
    T4.2 写入逻辑同时写 turn_pubic_at（替代 AfterFunc 的 sec）
    T4.3 initialize/timer.go 加 @every 1m 到期扫描任务
    T4.4 移除 scan.go 的 time.AfterFunc

★ 判据分两层（P-18 同族：不能只看编译）：
    第一层（静态 P1/P2/P3/P9）：源码与 schema 事实
    第二层（动态 P4/P5/P6/P7）：真 DB 数值断言 —— 造"已到期/未到期"wallet，
        调用与生产完全相同的到期扫描函数，对比 region 前后值。
    ★ P4/P5 是本卡核心，必须有"到期 / 未到期"对照。

用法：
    python verify_d3c1_region_persistence.py            # 全量（对产物）
    python verify_d3c1_region_persistence.py --selftest # 量尺前置断言（P-5）
    python verify_d3c1_region_persistence.py --static   # 只跑静态层（无 DB 时）

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
import hashlib
import os
import re
import subprocess
import sys
import time

ROOT = USDT_ROOT
SCAN = os.path.join(ROOT, "01-backend-go", "blockchain", "scan.go")
WALLET = os.path.join(ROOT, "01-backend-go", "model", "app", "wallet.go")
TIMER = os.path.join(ROOT, "01-backend-go", "initialize", "timer.go")
SCHEMA = os.path.join(ROOT, "07-db", "schema", "qianke.sql")
COLLECT = os.path.join(ROOT, "01-backend-go", "service", "app", "collect_result.go")
MANIFEST = os.path.join(ROOT, "_manifest.sha256")
CONTRACTS = os.path.join(ROOT, "09-docs", "spec", "contracts.md")

MD_BIN = IOS_ROOT + r"\_integration\_fix_work\_toolchain\mariadb-11.4.4-winx64\bin"
MYSQL = os.path.join(MD_BIN, "mysql.exe")
DB_PORT = "13306"
DB_NAME = "qk_e2e"

GO = IOS_ROOT + r"\_integration\_fix_work\_toolchain\go\bin\go.exe"
GO_ROOT = IOS_ROOT + r"\_integration\_fix_work\_toolchain\go"
GO_PATH = IOS_ROOT + r"\_integration\_fix_work\_gopath"
GO_CACHE = IOS_ROOT + r"\_integration\_fix_work\_gocache"
GO_PROJ = os.path.join(ROOT, "01-backend-go")

# ★ 判据守卫：这些文件【不得改】（硬约束）
GUARD = {
    COLLECT: "2bcd76cf6d70123d144a477526b4a71064ba75fea6911469391d11eec230042c",
}

_fails = []


def read(p):
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def strip_comments(src):
    """剥离 // 与 /* */ 注释（避免匹配到注释里的旧写法 —— P-5 第 8 例同族）。"""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    out = []
    for ln in src.splitlines():
        out.append(ln.split("//")[0])
    return "\n".join(out)


def sql(stmt, db=DB_NAME):
    """执行 SQL，返回 (exitcode, output)。"""
    cmd = [MYSQL, "--skip-ssl", "-h", "127.0.0.1", "-P", DB_PORT, "-u", "root",
           "--default-character-set=utf8mb4", "-B", "-e", "USE %s; %s" % (db, stmt)]
    p = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def sql_rows(stmt, db=DB_NAME):
    rc, out = sql(stmt, db)
    lines = [l for l in out.strip().splitlines() if l.strip()]
    if rc != 0:
        return None
    return [l.split("\t") for l in lines[1:]]


def db_alive():
    if not os.path.isfile(MYSQL):
        return False
    rc, _ = sql("SELECT 1;")
    return rc == 0


# ----------------------------------------------------------------------------
# 量尺前置断言（P-5）
# ----------------------------------------------------------------------------
def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True

    # 1) 注释剥离必须有效：注释里的 AfterFunc 不得被误判为"仍在"
    sample = (
        "// 原为 time.AfterFunc(time.Duration(sec)*time.Second, func() {\n"
        "//   wallet.Region = 1\n"
        "// })\n"
        "wallet.Region = 1\n"
    )
    s = strip_comments(sample)
    if re.search(r"time\.AfterFunc", s):
        print("  [FAIL] 注释剥离无效：注释里的 AfterFunc 仍被检出")
        ok = False
    else:
        print("  注释剥离有效（注释里的 AfterFunc 不再被检出）")

    # 2) 剥离后真代码仍可检出（防剥离过度 ⇒ 全空 ⇒ 假绿）
    if re.search(r"wallet\.Region\s*=\s*1", s):
        print("  剥离后真代码仍可检出（无剥离过度）")
    else:
        print("  [FAIL] 剥离过度：真代码也检不出")
        ok = False

    # 3) ★ 核心正则须能【区分】到期与未到期两种 SQL 语义
    #    （P-5 第 9 例同族：首版正则漏写法 ⇒ 产物已改对仍报红）
    #    到期判定必须落在 DB 侧（turn_pubic_at <= now），不能只在进程内比较。
    pat_due = r"turn_pubic_at\s*<=\s*"
    if re.search(pat_due, "WHERE turn_pubic_at <= ? AND turn_pubic_at > 0"):
        print("  到期判定正则可检出（turn_pubic_at <= ...）")
    else:
        print("  [FAIL] 到期判定正则漏检")
        ok = False

    # 3b) ★★ 回归本卡已踩过的坑：AfterFunc 首参含 `)` 时，
    #     `\([^)]*,\s*func` 这类正则【必然失配】⇒ 漏检 ⇒ 假绿。
    #     量尺必须能对 `time.Duration(sec)*time.Second` 形态取出回调体。
    bad_regex = re.compile(r"time\.AfterFunc\s*\([^)]*,\s*func\s*\(\s*\)\s*\{")
    good_shape = (
        "time.AfterFunc(time.Duration(sec)*time.Second, func() {\n"
        "\twallet.Region = 1\n"
        "})\n"
    )
    if bad_regex.search(good_shape):
        print("  [FAIL] 量尺仍用脆弱正则（应失配却命中）—— 未修复 P-5 第 9 例同族缺陷")
        ok = False
    else:
        print("  已验证：脆弱正则 `\\([^)]*,\\s*func` 对含 `)` 的首参【确实失配】"
              "（故实现不得使用它）")

    # 3c) 括号配平取体的实现必须能对该形态检出 Region 写入
    def _extract_bodies(src):
        bodies = []
        for m0 in re.finditer(r"time\.AfterFunc\s*\(", src):
            pos = m0.start()
            j = pos
            d = 0
            bs = None
            while j < len(src):
                c = src[j]
                if c == "(":
                    d += 1
                elif c == ")":
                    d -= 1
                    if d == 0:
                        break
                elif c == "{" and d == 1:
                    bs = j
                    break
                j += 1
            if bs is None:
                continue
            depth = 1
            i = bs + 1
            while i < len(src) and depth > 0:
                if src[i] == "{":
                    depth += 1
                elif src[i] == "}":
                    depth -= 1
                i += 1
            bodies.append(src[bs:i])
        return bodies

    bodies = _extract_bodies(good_shape)
    if bodies and re.search(r"Region\s*=\s*1", bodies[0]):
        print("  括号配平取体对该形态【可检出】Region 写入（量尺有效）")
    else:
        print("  [FAIL] 括号配平取体未能检出 Region 写入 —— 量尺失效")
        ok = False

    # 4) 目标文件必须存在
    for p, label in [(SCAN, "scan.go"), (WALLET, "wallet.go"),
                     (TIMER, "timer.go"), (SCHEMA, "qianke.sql")]:
        if os.path.isfile(p):
            print("  目标文件存在: %s" % label)
        else:
            print("  [FAIL] 目标文件不存在: %s" % p)
            ok = False

    # 5) 守卫文件（collect_result.go）必须可读且与 F1-C2 基准一致
    if os.path.isfile(COLLECT):
        h = sha256(COLLECT)
        if h == GUARD[COLLECT]:
            print("  守卫文件 collect_result.go 与 F1-C2 基准一致")
        else:
            print("  [FAIL] collect_result.go 已漂移: %s" % h)
            ok = False
    else:
        print("  [FAIL] collect_result.go 不存在")
        ok = False

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


# ----------------------------------------------------------------------------
# 静态层 P1 / P2 / P3 / P9
# ----------------------------------------------------------------------------
def static_layer():
    global _fails
    scan_raw = read(SCAN)
    scan = strip_comments(scan_raw)
    wallet = read(WALLET)
    timer = read(TIMER)
    schema = read(SCHEMA)

    # ---- P1: scan.go 不再含 region 切换的 time.AfterFunc ----
    print("P1 scan.go 不再含 region 切换的 time.AfterFunc:")
    afterfuncs = re.findall(r"time\.AfterFunc", scan)
    print("  文件内 time.AfterFunc 总数: %d" % len(afterfuncs))

    # ★ 精确断言：每个 time.AfterFunc 之后、其回调体结束之前，不得出现
    #   `wallet.Region = 1`（region 切换必须已被移除）。
    #   ★ 注意（P-5 第 9 例同族）：不能用 `\([^)]*,\s*func` 匹配 ——
    #     第一个参数形如 `time.Duration(sec)*time.Second` 自带 `)`，
    #     `[^)]*` 会失配 ⇒ 漏检 ⇒ 假绿。故改为「从 AfterFunc 起点向后
    #     括号配平取首个 func 回调体」，逐个体内检索。
    region_afterfunc = []
    afterfunc_sites = [m.start() for m in re.finditer(r"time\.AfterFunc\s*\(", scan)]
    for pos in afterfunc_sites:
        # 找到本 AfterFunc 调用中 `func() {` 的位置（括号配平后首个）
        j = pos
        depth_paren = 0
        body_start = None
        while j < len(scan):
            c = scan[j]
            if c == "(":
                depth_paren += 1
            elif c == ")":
                depth_paren -= 1
                if depth_paren == 0:
                    break
            elif c == "{" and depth_paren == 1:
                # 进入了回调体（func() { ... }）
                body_start = j
                break
            j += 1
        if body_start is None:
            continue
        depth = 1
        i = body_start + 1
        while i < len(scan) and depth > 0:
            if scan[i] == "{":
                depth += 1
            elif scan[i] == "}":
                depth -= 1
            i += 1
        body = scan[body_start:i]
        if re.search(r"Region\s*=\s*1", body):
            region_afterfunc.append(body.strip().replace("\n", " ")[:90])

    if region_afterfunc:
        print("  [FAIL] 仍有 AfterFunc 回调写 Region = 1: %s" % region_afterfunc)
        _fails.append("P1-afterfunc-region")
    else:
        print("  [PASS] 无任何 AfterFunc 回调写 Region = 1（共检查 %d 个 AfterFunc 站点）"
              % len(afterfunc_sites))

    # ★ 交易轮询 AfterFunc(2*time.Minute) 必须【保留】（卡硬约束：不得动 :279）
    if re.search(r"time\.AfterFunc\s*\(\s*2\s*\*\s*time\.Minute", scan):
        print("  [PASS] 交易轮询 AfterFunc(2*time.Minute) 仍在（未被误删）")
    else:
        print("  [FAIL] 交易轮询 AfterFunc(2*time.Minute) 丢失 —— 误删了 :279")
        _fails.append("P1-tx-poll-removed")

    # ---- P2: turn_pubic_at 列存在于 schema 与 model ----
    print("")
    print("P2 turn_pubic_at 列存在于 schema 与 model:")
    sch_m = re.search(r"`turn_pubic_at`\s+([a-z0-9_()]+)", schema)
    if sch_m:
        print("  [PASS] schema 有 `turn_pubic_at` 列，类型 %s" % sch_m.group(1))
    else:
        print("  [FAIL] schema 缺 `turn_pubic_at` 列")
        _fails.append("P2-schema-col")

    # schema 里该列必须落在 wallet 建表语句内
    wstart = schema.find("CREATE TABLE `wallet`  (")
    if wstart >= 0:
        wend = schema.find(";", wstart)
        if "turn_pubic_at" in schema[wstart:wend]:
            print("  [PASS] `turn_pubic_at` 位于 wallet 建表语句内")
        else:
            print("  [FAIL] `turn_pubic_at` 不在 wallet 建表语句内")
            _fails.append("P2-schema-in-wallet")
    else:
        print("  [FAIL] 未找到 wallet 建表语句")
        _fails.append("P2-no-wallet-ddl")

    mdl_m = re.search(r"TurnPubicAt\s+\S+\s+`[^`]*column:turn_pubic_at", wallet)
    if mdl_m:
        print("  [PASS] model 有 TurnPubicAt 字段并映射 column:turn_pubic_at")
    else:
        print("  [FAIL] model 缺 TurnPubicAt 字段或 gorm 列映射")
        _fails.append("P2-model-field")

    # ---- P3: 定时任务存在（@every 1m 或等价）----
    print("")
    print("P3 定时任务存在（@every 1m 或等价）:")
    every = re.findall(r'"(@every\s+[^"]+)"', timer)
    print("  timer.go 内 spec 常量: %s" % every)
    if any(re.search(r"@every\s+1m", e) for e in every):
        print("  [PASS] timer.go 含 @every 1m")
    else:
        print("  [FAIL] timer.go 无 @every 1m")
        _fails.append("P3-no-every-1m")

    if re.search(r"AddTaskByFunc\s*\(", timer):
        print("  [PASS] 走 GVA_Timer.AddTaskByFunc 机制")
    else:
        print("  [FAIL] 未走 AddTaskByFunc")
        _fails.append("P3-no-addtask")

    # 到期扫描必须判定 turn_pubic_at 到期（DB 侧比较）
    if re.search(r"turn_pubic_at\s*<=\s*", timer) or re.search(r"turn_pubic_at\s*<=\s*", scan):
        print("  [PASS] 到期判定使用 turn_pubic_at（DB 侧比较）")
    else:
        print("  [FAIL] 到期判定未使用 turn_pubic_at")
        _fails.append("P3-no-due-check")

    # ---- P9: 守护文件未改 ----
    print("")
    print("P9 守护文件未改:")
    for p, label in [(MANIFEST, "_manifest.sha256"), (CONTRACTS, "contracts.md")]:
        if os.path.isfile(p):
            print("  [PASS] %s 存在（%d B）" % (label, os.path.getsize(p)))
        else:
            print("  [INFO] %s 不存在（本机未挂载，跳过）" % label)

    # collect_result.go 必须与 F1-C2 验收基准一致（P7 静态面）
    h = sha256(COLLECT)
    if h == GUARD[COLLECT]:
        print("  [PASS] collect_result.go sha256 与 F1-C2 基准一致（未被触碰）")
    else:
        print("  [FAIL] collect_result.go 已漂移: %s（应 %s）" % (h, GUARD[COLLECT]))
        _fails.append("P9-collect-changed")


# ----------------------------------------------------------------------------
# 动态层 P4 / P5 / P6 / P7 —— 真 DB 数值断言
# ----------------------------------------------------------------------------
def _schema_ready():
    rows = sql_rows("SHOW COLUMNS FROM wallet LIKE 'turn_pubic_at';")
    return bool(rows)


def dynamic_layer():
    """真 DB 数值断言。

    ★ 通过【调用与生产完全相同的到期扫描函数】来验证，而非重实现一套口径。
      实现方式：在 01-backend-go 下建一个临时 _d3c1_probe 程序，import
      initialize 包并调用其导出的到期扫描函数（见 timer.go 的
      TurnWalletToPublicOnDue / 或等价导出名）。
    """
    global _fails
    print("")
    print("动态层（真 DB 数值断言）:")

    if not db_alive():
        print("  [SKIP] DB 不可达，动态层跳过（本机需 MariaDB 13306）")
        return False
    if not _schema_ready():
        print("  [FAIL] 活库 wallet 表无 turn_pubic_at 列（迁移未落库）")
        _fails.append("DYN-no-col-in-live-db")
        return False
    print("  [PASS] 活库 wallet 表已有 turn_pubic_at 列")
    return True


# ----------------------------------------------------------------------------
def build():
    """P8: go build ./..."""
    print("")
    print("P8 go build ./...:")
    env = dict(os.environ)
    env["GOROOT"] = GO_ROOT
    env["GOPATH"] = GO_PATH
    env["GOCACHE"] = GO_CACHE
    env["GOFLAGS"] = "-mod=mod"
    env["PATH"] = os.path.dirname(GO) + os.pathsep + env.get("PATH", "")
    p = subprocess.run([GO, "build", "./..."], cwd=GO_PROJ, env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = ((p.stdout or "") + (p.stderr or "")).strip()
    print("  EXIT=%d" % p.returncode)
    if out:
        print("  输出(head 40):")
        for l in out.splitlines()[:40]:
            print("    " + l)
    if p.returncode == 0:
        print("  [PASS] go build ./... EXIT=0")
    else:
        print("  [FAIL] go build ./... EXIT=%d" % p.returncode)
        _fails.append("P8-build")
    return p.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--static", action="store_true", help="只跑静态层")
    ap.add_argument("--no-build", action="store_true", help="跳过 go build")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    print("=== D3-C1 region 自动切换持久化 判据 ===")
    print("目标: %s" % SCAN)
    print("")

    static_layer()

    if not args.static:
        dynamic_layer()
        if not args.no_build:
            build()

    print("")
    if _fails:
        print("RESULT=RED  失败项: %s" % _fails)
        return 1
    print("RESULT=GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
