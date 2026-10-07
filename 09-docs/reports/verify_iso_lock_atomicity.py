# -*- coding: utf-8 -*-
"""判据：iso_run.py 单实例锁（acquire_lock）的**原子性**。

★ 出处：安卓线独立复核件 F-01 自己写下的 ACCEPTANCE ——
    「用**同步屏障**让两进程同一微秒进 `acquire_lock` ⇒ 只有一个能过」。
    本脚本就是这条 ACCEPTANCE 的可复跑实现（F-01 原文只登记未执行）。

判据（落在一个同名量上：**同步屏障下拿到锁的进程数 winners**）：
    断言  winners <= 1
    · 现版 check-then-act（exists → open("w")）  ⇒ 预期 **RED**（winners = 2）
    · 原子对照 O_CREAT|O_EXCL                    ⇒ 预期 **GREEN**（winners = 1）
    ⇒ 「改坏它 ⇒ 断言必须红」在本件上的体现：把原子创建换成非原子，断言就从 GREEN 变 RED。

安全：**不触碰真锁**（把 iso_run.LOCK 改指临时路径）、**不起任何服务**、**不占共享端口**。

用法：
    python verify_iso_lock_atomicity.py            # 全量（含原子对照）
    python verify_iso_lock_atomicity.py --selftest # 量尺前置断言
退出码：0 = 断言过（GREEN）；1 = 断言红（即发现缺陷）；2 = 量尺自检坏。
"""
from __future__ import annotations

import os as _os
import sys as _sys

_os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

ISO_RUN = _os.environ.get("ISO_RUN_PY", r"E:\ios漏洞\_integration\_fix_work\iso_run.py")
FW = os.path.dirname(ISO_RUN)
BREACH = 2          # 两进程都拿到锁
ROUNDS_DEFAULT = 20


# ---------------- role: 子进程侧 ----------------
def role_worker(mode, lock, start, hold):
    """mode=real   -> 调用 iso_run 的【真】acquire_lock
       mode=atomic -> O_CREAT|O_EXCL 原子创建（对照）"""
    sys.path.insert(0, FW)
    import iso_run                                                  # noqa: E402
    iso_run.LOCK = lock                                             # 隔离：真锁零风险

    while time.time() < float(start):                               # 同步屏障
        pass

    if mode == "real":
        try:
            iso_run.acquire_lock()                                  # ← 被判据点
        except RuntimeError:
            print("REFUSE"); return 0
        print("WIN")
        time.sleep(float(hold))
        iso_run.release_lock()
        return 0

    try:                                                            # 原子对照
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode()); os.close(fd)
    except FileExistsError:
        print("REFUSE"); return 0
    print("WIN")
    time.sleep(float(hold))
    try:
        os.remove(lock)
    except OSError:
        pass
    return 0


# ---------------- 判据本体 ----------------
def _spawn_pair(mode, delay=0.0, rounds=ROUNDS_DEFAULT, barrier=True):
    wins_per_round = []
    for _ in range(rounds):
        d = tempfile.mkdtemp(prefix="isolock_")
        lock = os.path.join(d, "_lock")
        start = time.time() + 1.5 if barrier else 0.0
        ps = [subprocess.Popen([sys.executable, os.path.abspath(__file__), "--role", mode,
                                "--lock", lock, "--start", str(start), "--hold", "0.2"],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
              for _ in range(2)]
        if delay:                                                   # 错峰：等第一个真拿到锁
            time.sleep(delay)
        out = [p.communicate()[0].strip() for p in ps]
        wins_per_round.append(sum(1 for o in out if o == "WIN"))
        shutil.rmtree(d, ignore_errors=True)
        time.sleep(0.03)
    return wins_per_round


def _is_non_atomic(src_text):
    """静态判据：acquire 路径是否为 check-then-act（无 O_EXCL）。"""
    return (re.search(r"os\.path\.exists\(\s*LOCK\s*\)", src_text) is not None
            and re.search(r"open\(\s*LOCK\s*,\s*[\"']w[\"']", src_text) is not None
            and "O_EXCL" not in src_text)


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    fake = 'if os.path.exists(LOCK):\n    pass\nwith open(LOCK, "w") as fh: fh.write("x")\n'
    if not _is_non_atomic(fake):
        print("  [FAIL] 非原子检测器抓不到合成样本"); ok = False
    else:
        print("  [PASS] 非原子检测器有效（抓不到就该红）")
    fake_atomic = 'fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)\n'
    if _is_non_atomic(fake_atomic):
        print("  [FAIL] 对原子样本误报为非原子"); ok = False
    else:
        print("  [PASS] 原子样本无误报")
    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--role"); ap.add_argument("--lock"); ap.add_argument("--start")
    ap.add_argument("--hold")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--rounds", type=int, default=ROUNDS_DEFAULT)
    a = ap.parse_args()

    if a.role:
        return role_worker(a.role, a.lock, a.start, a.hold)
    if a.selftest:
        return selftest()

    print("=== iso_run 单实例锁 · 原子性判据 ===")
    print(f"  目标：{ISO_RUN}")
    with open(ISO_RUN, encoding="utf-8") as fh:
        src = fh.read()
    import hashlib
    print(f"  sha256={hashlib.sha256(src.encode('utf-8')).hexdigest()}  bytes={len(src.encode('utf-8'))}")

    non_atomic = _is_non_atomic(src)
    print(f"  [静态] check-then-act（无 O_EXCL）: {non_atomic}")

    fails = []

    print(f"\n  [A] 现版真 acquire_lock · 同步屏障 · N=2 · rounds={a.rounds}")
    wA = _spawn_pair("real", rounds=a.rounds)
    breachA = sum(1 for w in wA if w > 1)
    print(f"      winners/round={wA}")
    print(f"      击穿（winners>1）= {breachA}/{a.rounds} = {100*breachA/a.rounds:.1f}%")
    if any(w > 1 for w in wA):
        fails.append(f"A-atomicity-breach:{breachA}/{a.rounds}")
        print("      ⇒ ★ 断言 RED：同一时刻有两个持有者 ⇒ 锁不是互斥的")
    else:
        print("      ⇒ 断言 GREEN")

    print("\n  [B] 现版真 acquire_lock · 错峰 1.2s（P1 持锁 3s）· 应 REFUSE")
    # 错峰：先起一个持锁 3s 的，再起一个
    d = tempfile.mkdtemp(prefix="isolock_"); lock = os.path.join(d, "_lock")
    p1 = subprocess.Popen([sys.executable, os.path.abspath(__file__), "--role", "real",
                           "--lock", lock, "--start", "0", "--hold", "3.0"],
                          stdout=subprocess.PIPE, text=True)
    time.sleep(1.2)
    p2 = subprocess.Popen([sys.executable, os.path.abspath(__file__), "--role", "real",
                           "--lock", lock, "--start", "0", "--hold", "0.1"],
                          stdout=subprocess.PIPE, text=True)
    o1 = p1.communicate()[0].strip(); o2 = p2.communicate()[0].strip()
    shutil.rmtree(d, ignore_errors=True)
    print(f"      (P1,P2)=({o1},{o2})  ⇒ {'正确拒绝 ✅' if (o1,o2)==('WIN','REFUSE') else '异常'}")
    if (o1, o2) != ("WIN", "REFUSE"):
        fails.append("B-stagger")

    print(f"\n  [C] 原子对照 O_CREAT|O_EXCL · 同步屏障 · N=2 · rounds={a.rounds}")
    wC = _spawn_pair("atomic", rounds=a.rounds)
    breachC = sum(1 for w in wC if w > 1)
    print(f"      winners/round={wC}")
    print(f"      击穿 = {breachC}/{a.rounds}  ⇒ {'GREEN（对照有效：原子创建真互斥）' if breachC == 0 else '对照异常'}")

    print("\n=== 结论 ===")
    if fails:
        print(f"RESULT=RED  {fails}")
        print("  ⇒ 复现了 F-01：现版锁在同步屏障下**不互斥**；F-10（并发互撞）据此**未闭合**。")
        return 1
    print("RESULT=GREEN  锁在同步屏障下互斥")
    return 0


if __name__ == "__main__":
    sys.exit(main())
