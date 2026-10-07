# -*- coding: utf-8 -*-
"""T29（WBE01-D · (乙-1)）**隔离运行入口** —— 一条命令跑完全程。

    起实例 B（8900 / qk_e2e_test）→ 播种 → 跑判据（带 DSH_DB/DSH_API）→ 停实例 B → 报告

★ **全程不动共享 8888**（只起/停 8900）。
★ **护栏指向业务库 `qk_e2e`**：跑前/跑后各取一次 (行数, 内容哈希) ⇒ 证"业务库一个字没碰"。
★ 启动/结束时都打印**连的哪个库 / 哪个 API**（§4-7 响亮提示）。

用法：
    python iso_run.py                 # 全流程
    python iso_run.py --no-stop       # 跑完保留实例 B（便于手工复跑）
    python iso_run.py --keep-seed     # 不重新播种
"""
from __future__ import annotations

import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
import sys as _sys

_os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import argparse
import hashlib
import os
import subprocess
import sys
import time
import urllib.request

FW = IOS_ROOT + r"\_integration\_fix_work"
ISO_EXE = os.path.join(FW, r"_wbe01d_bak\_i2c1_server_iso.exe")
ISO_WS = os.path.join(FW, "_wbe01d_ws")          # cwd ⇒ 决定它读哪份 config.yaml
ISO_PORT = "8900"
ISO_API = f"http://127.0.0.1:{ISO_PORT}"
DST_DB = "qk_e2e_test"
SRC_DB = "qk_e2e"                                 # 业务库（护栏对象，只读）
MYSQL = os.path.join(FW, r"_toolchain\mariadb-11.4.4-winx64\bin\mysql.exe")
REDIS_CLI = os.path.join(FW, r"_toolchain\redis\redis-cli.exe")
REDIS_PORT = "16379"
# ★ T30：隔离实例的 `redis.db` = 1（见 `_wbe01d_ws/config.yaml`）；
#   而**护栏永远查主栈那个库（db 0）** —— 它要证的正是"主栈 Redis 一个字没碰"。⛔ 不跟随隔离实例。
GUARD_REDIS_DB = os.environ.get("DSH_GUARD_REDIS_DB", "0")

SUITE = ["verify_f1c9_toaddress_guard.py",
         "verify_f1c8_amount_guard.py",
         "verify_money_path.py"]

GUARD_TABLES = ["bill", "settlement", "token", "wallet", "custom", "agent", "packet", "machine"]


# ---------- 基础设施 ----------
def sql_row(stmt, db):
    cmd = [MYSQL, "--skip-ssl", "-h", "127.0.0.1", "-P", "13306", "-u", "root",
           "--default-character-set=utf8mb4", "-B", "-e", f"USE {db}; {stmt}"]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    ls = [l for l in (p.stdout or "").strip().splitlines() if l.strip()]
    return ls[1].split("\t") if len(ls) > 1 else None


def db_snapshot(tag):
    """业务库快照：{表: (行数, 全表内容哈希)}。★ 永远查业务库 SRC_DB，⛔ 不跟随 DSH_DB。

    ★★ 列**动态取**（information_schema）—— 先前写死 `role/status/usdt_num/settlement_id` 是 `bill` 专有列，
       对其它表 SQL 报错 ⇒ 全部读数变 None ⇒ **假报警**（本线自造，已实测）。"""
    snap = {}
    for t in GUARD_TABLES:
        cols = _cols_of(SRC_DB, t)
        if not cols:
            snap[t] = (None, None)
            continue
        order = "id" if "id" in cols else cols[0]
        expr = "MD5(CONCAT_WS('|'," + ",".join(f"COALESCE(`{c}`,'<NULL>')" for c in cols) + "))"
        r = sql_row(f"SET SESSION group_concat_max_len=10485760; "
                    f"SELECT COUNT(*), COALESCE(MD5(GROUP_CONCAT(h ORDER BY `{order}` SEPARATOR '')),'-') "
                    f"FROM (SELECT {expr} AS h, `{order}` FROM `{t}`) x;", SRC_DB)
        snap[t] = (int(r[0]), r[1]) if r and len(r) >= 2 else (None, None)
    print(f"  [业务库/{tag}] " + " ".join(
        f"{t}={snap[t][0]}/{ (snap[t][1] or 'n/a')[:8] }" for t in GUARD_TABLES))
    return snap


def _cols_of(db, t):
    r = subprocess.run([MYSQL, "--skip-ssl", "-h", "127.0.0.1", "-P", "13306", "-u", "root", "-B", "-e",
                        f"SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='{db}' "
                        f"AND TABLE_NAME='{t}' ORDER BY ORDINAL_POSITION;"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    ls = [l for l in (r.stdout or "").strip().splitlines() if l.strip()]
    return ls[1:] if len(ls) > 1 else []


def db_diff(before, after):
    bad = []
    for t in GUARD_TABLES:
        b, a = before.get(t, (None, None)), after.get(t, (None, None))
        if b[0] is None or a[0] is None:
            bad.append(f"{t}: 读数不可得(结论不完整)")
        elif b[0] != a[0]:
            bad.append(f"{t}: 行数 {b[0]}→{a[0]}")
        elif (b[1] or "") != (a[1] or ""):
            bad.append(f"{t}: 行数同、内容哈希变 {(b[1] or '')[:8]}→{(a[1] or '')[:8]}")
    return bad


def _redis_keys(db):
    """取该 Redis 库的全部键。返回 (键数, 键名有序拼接的 md5)。

    ★★ ⌛2026-10-03 实测：**本机这份 `redis-cli` 的 `--scan` 静默返回空**（退出码 0、无任何输出，
       而同一时刻 `DBSIZE`=1、`KEYS '*'` 能列出该键）⇒ 若用它，护栏会**恒报 0 键 ⇒ 永不报警**
       （＝本项目「恒绿的检查＝没有检查」那条）。故**改用 `KEYS '*'`**：
       对 db0/本测试库这种键数极少的场景，阻塞风险可接受；⛔ **不得**在键多的大库上用它。"""
    r = subprocess.run([REDIS_CLI, "-h", "127.0.0.1", "-p", REDIS_PORT, "-n", str(db), "KEYS", "*"],
                       capture_output=True, text=True, errors="replace")
    keys = sorted(k.strip() for k in (r.stdout or "").splitlines() if k.strip())
    return len(keys), (hashlib.md5("\n".join(keys).encode("utf-8")).hexdigest() if keys else "-")


def redis_snapshot(tag):
    """★ T30 护栏：**主栈 Redis（db `GUARD_REDIS_DB`）** 的键集快照 —— 键数 ＋ 键名哈希。
    ⛔ 永不跟随隔离实例的 `redis.db`（那是 1）。"""
    n, h = _redis_keys(GUARD_REDIS_DB)
    n1, h1 = _redis_keys("1")
    print(f"  [Redis/{tag}] 主栈 db{GUARD_REDIS_DB}: keys={n} hash={h[:8]}"
          f"   ｜ 隔离 db1: keys={n1} hash={h1[:8]}")
    return (n, h)


def redis_diff(before, after):
    bad = []
    if before[0] is None or after[0] is None:
        bad.append("键数读数不可得")
    elif before[0] != after[0]:
        bad.append(f"主栈 db{GUARD_REDIS_DB} 键数 {before[0]}→{after[0]}")
    elif before[1] != after[1]:
        bad.append(f"主栈 db{GUARD_REDIS_DB} 键数同、键名哈希变 {before[1][:8]}→{after[1][:8]}")
    return bad


def wait_health(timeout=180):
    dl = time.time() + timeout
    while time.time() < dl:
        try:
            with urllib.request.urlopen(ISO_API + "/health", timeout=5) as r:
                return r.status == 200, r.read().decode("utf-8", "replace")
        except Exception:
            time.sleep(5)
    return False, "(超时)"


def _netstat_pids():
    """监听 ISO_PORT 的 PID 集（★ F-06：`errors="replace"`，与其余 7 处 subprocess 一致）。"""
    r = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, errors="replace")
    return {l.split()[-1] for l in (r.stdout or "").splitlines()
            if "LISTENING" in l and f":{ISO_PORT} " in l}


def verify_iso_identity():
    """★ F-07（复核 finding）：端口已被占用时**必须校验身份**，⛔ 不能盲目复用。

    判据两条（缺一不可）：① `/health` 通；② 该 PID 的**映像名** == 本隔离实例的 exe 名。
    返回：`None` ⇒ 端口空闲（可正常启动）· `True` ⇒ 是我们的实例（可复用）· `False` ⇒ 拒绝复用。
    """
    pids = _netstat_pids()
    if not pids:
        return None
    pid = sorted(pids)[0]
    r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                       capture_output=True, text=True, errors="replace")
    rows = [l for l in (r.stdout or "").strip().splitlines() if l.strip()]
    img = rows[0].split(",")[0].strip('"') if rows else ""
    want = os.path.basename(ISO_EXE)
    ok_health, body = wait_health(timeout=15)
    print(f"  [probe] {ISO_PORT} 已被占用：PID={pid} image={img!r}（期望 {want!r}）"
          f" · /health={body[:60] if ok_health else '(不通)'}")
    return ok_health and (img.lower() == want.lower())


def start_iso():
    st = verify_iso_identity()
    if st is True:
        print(f"  [skip] {ISO_PORT} 由**本隔离实例**监听（身份校验通过）⇒ 复用")
        return None
    if st is False:
        # ★ F-07：绝不"盲复用"——跑在未知目标上，判据结论无意义
        raise RuntimeError(f"★ 拒绝复用：{ISO_PORT} 被占用，但身份校验未通过（不是 {os.path.basename(ISO_EXE)}）")
    print(f"  [start] {ISO_EXE}\n          cwd={ISO_WS}")
    # ★ 清代理变量（P-30：Start-Process 会因 NO_PROXY 字典键冲突失败）
    env = {k: v for k, v in os.environ.items()
           if k.lower() not in ("no_proxy", "http_proxy", "https_proxy", "all_proxy")}
    out = open(os.path.join(ISO_WS, "_svc_iso.out"), "ab")
    err = open(os.path.join(ISO_WS, "_svc_iso.err"), "ab")
    cf = 0x08000000 if os.name == "nt" else 0      # CREATE_NO_WINDOW
    p = subprocess.Popen([ISO_EXE], cwd=ISO_WS, stdout=out, stderr=err, creationflags=cf, env=env)
    return p


def stop_iso():
    pids = _netstat_pids()
    for pid in pids:
        print(f"  [stop] PID {pid}（{ISO_PORT}）")
        # ★ F-06：补 `errors="replace"`（中文 Windows 下 taskkill 输出为 GBK，原缺此项 ⇒ UnicodeDecodeError）
        subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True, text=True,
                       errors="replace")
    return bool(pids)


def fixture_cuid():
    """读**隔离库**的夹具态（`packet.custom_user_id`）。"""
    r = sql_row("SELECT custom_user_id FROM packet WHERE id = 1;", DST_DB)
    return int(r[0]) if r and r[0].lstrip("-").isdigit() else 0


def set_fixture_cuid(v):
    """★ F-08：翻转夹具态 —— 只动**隔离库** `qk_e2e_test`，⛔ 从不碰业务库。"""
    subprocess.run([MYSQL, "--skip-ssl", "-h", "127.0.0.1", "-P", "13306", "-u", "root",
                    "-e", f"UPDATE `{DST_DB}`.packet SET custom_user_id = {int(v)} WHERE id = 1;"],
                   capture_output=True, text=True, errors="replace")


LOCK = os.path.join(FW, "_iso_run.lock")
# ★★ T60 返修（`F-T60-A1`）：**不可解析**的锁（空／非数字）**只有"够老"才允许接管** ——
#    fail-closed；★ 这个阈值同时保住 `<创建 → 写 PID>` 之间崩溃时的**自愈**（⛔ 不把自愈改没）。
LOCK_OPAQUE_STALE_SECONDS = int(os.environ.get("ISO_RUN_LOCK_STALE_SECONDS", "300"))
# ★★ T60 返修（第二次）：**接管令牌** —— 接管动作必须串行，否则"多人同时接管"会把活锁搬走。
TAKE_TOKEN = LOCK + ".take"
TAKE_TOKEN_STALE_SECONDS = int(os.environ.get("ISO_RUN_TAKE_TOKEN_STALE_SECONDS", "10"))
# ★★ T74 返修（`F-T60-B3`）：本机 `E:` 卷是 **exFAT** ⇒ 其 mtime 以 **2 s** 为粒度且**向上取整**
#   （12 次采样实测 `mtime − time.time() ∈ [+0.07, +1.96]`，恒为正）⇒ `time.time() - getmtime`
#   **低估**文件真实年龄最多 2 s ⇒ 一切"够老"判定的**实际生效点比标称阈值晚 0–2 s**。
#   ⇒ 对用户**承诺的等待时长**一律按 `+2 s` 计（★ ⛔ 不动阈值本身：该偏差方向 fail-closed，改它只会削弱余量）。
MTIME_GRANULARITY_SLACK_SECONDS = 2


def _pid_alive_tasklist(pid):
    """`tasklist` 全量扫描版（**仅作兜底**）：拉全量 CSV，逐行比对 PID 列（第 2 列）。
    ★ 不依赖任何**本地化提示文本**；★ fail-closed：命令失败／无输出 ⇒ **按活**。"""
    try:
        r = subprocess.run(["tasklist", "/FO", "CSV", "/NH"],
                           capture_output=True, text=True, errors="replace", timeout=30)
    except Exception:
        return True
    out = r.stdout or ""
    if r.returncode != 0 or not out.strip():
        return True
    want = str(pid)
    for line in out.splitlines():
        if line.startswith('"'):
            cols = line.split('","')
            if len(cols) >= 2 and cols[1].strip('"') == want:
                return True
    return False


def _pid_alive(pid):
    """★ 判 PID 是否存活（★★ `T60` 返修后的**内核直查**版）。

    ⚠️ 沿革与**两个坑**：
      · `F-09`（⌛2026-10-03）：`tasklist /FI …` 无匹配时把提示行打到 stdout ⇒ 只看"有没有输出"
        会把**任何** PID 判成活 ⇒ 锁永久卡死。当时改判「首字符是不是 `"`」。
      · ★★ `F-T60-A1` 的**真正根因**（⌛2026-10-05，本线仪器化实测）：**`tasklist` 在<并发抢锁>时
        会偶发查不到<活>进程** —— 同一瞬间 14 个进程查到 `PID 7384`、**1 个查不到**，该进程遂判其
        「死」⇒ 走陈旧分支 ⇒ **搬走活锁 ⇒ 两进程同持**（N=16 实测 6/20、N=8 偶发）。
        ⇒ **`tasklist` 不是可靠的探活器**（它靠快照枚举，抢锁时与进程表竞争）。
      ⇒ ★ 改用**内核直查**：`OpenProcess(SYNCHRONIZE)` ⇒ `WaitForSingleObject(h, 0)`：
         `WAIT_TIMEOUT(258)` ＝ 还在跑；`WAIT_OBJECT_0(0)` ＝ 已退出。**不枚举、不解析任何文本**。
      ⇒ ★ **fail-closed**：调用异常／句柄语义不明 ⇒ **按"活"**（⛔ 绝不因"查不动"就接管一把可能活着的锁）。"""
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        SYNCHRONIZE = 0x00100000
        WAIT_TIMEOUT = 258
        h = k32.OpenProcess(SYNCHRONIZE, False, int(pid))
        if not h:
            # ★ 拿不到句柄（进程不存在／权限不足，二者不可区分）⇒ 退到 tasklist 全量扫描再判
            return _pid_alive_tasklist(pid)
        try:
            return k32.WaitForSingleObject(h, 0) == WAIT_TIMEOUT
        finally:
            k32.CloseHandle(h)
    except Exception:
        return True


class LockBusy(RuntimeError):
    """★ T60 返修（`F-T60-A3`）：**有人在跑**（或锁不可解析而 fail-closed 拒绝）——
       上位应「等／退出」，⛔ **与「重试耗尽」区分**（两者原先同型 `RuntimeError`）。"""


class LockContention(RuntimeError):
    """★ T60 返修（`F-T60-A3`）：**重试耗尽**（疑似多条线同时抢）—— ⛔ 与「有人在跑」区分。"""


def _read_lock_owner():
    """读锁内容 ⇒ `(state, pid)`，`state ∈ {'absent','alive','dead','opaque'}`。

    ★★ T60 返修（`F-T60-A1`）：**空／非数字 ⇒ `'opaque'`** —— ⛔ **不再**直接当"陈旧"去接管；
       否则会踩到「`os.open(O_CREAT|O_EXCL)` 刚建**空文件**、PID 还没写」那一瞬 ⇒ **把活锁搬走**。"""
    try:
        raw = open(LOCK, encoding="utf-8", errors="replace").read().strip()
    except FileNotFoundError:
        return "absent", None
    except OSError:
        return "opaque", None
    if raw.isdigit():
        pid = int(raw)
        return ("alive" if _pid_alive(pid) else "dead"), pid
    return "opaque", None


def _opaque_lock_is_old():
    """★ fail-closed 的**唯一**放行条件：不可解析**且**够老（mtime 超阈值）⇒ 才可按陈旧接管。
    ⇒ ★ 既**不**把"刚建好、还没写 PID 的活锁"当陈旧搬走，又**保住**崩溃后的自愈。"""
    try:
        age = time.time() - os.path.getmtime(LOCK)
    except OSError:
        return False
    return age >= LOCK_OPAQUE_STALE_SECONDS


# ★★ T74 修订（第 2 名 `F-1` · P1）：**本进程自己的观察窗口** —— 「同一个令牌**内容**被我们连续
#    看到多久」。★ 键＝**内容**、尺＝**本进程的钟** ⇒ 与文件时间戳**无关**（⛔ 不受"沿用"污染）。
_OPAQUE_TOKEN_SEEN = {}


def _take_token_is_live():
    """★ T74 修订（第 2 名 `F-1` · **P1**）：判「令牌是否<ins>被活持有者持着</ins>」—— ★★ ⛔ **绝不看文件时间戳**。

    ★★ 为什么（根因，两条腿独立量到）：本机 `E:` 卷上，**同名文件被删后重建会<ins>沿用</ins>旧时间戳**
      ⇒ `getmtime`／`getctime` 都读出**比实际老**的假值。旧法"够老（≥ `TAKE_TOKEN_STALE_SECONDS`）就删"
      据此**删掉<ins>活持有者</ins>的令牌** ⇒ 两进程同入**接管临界区** ⇒ ★★ **该锁恰在"崩溃残留"这个
      最需要它的场景下失效**（实测 `N=16` ＋ 预置陈旧锁 ⇒ **`4/20` 轮真并发多持**）✓

    ★ 判据（★ 三层，**全部与时间戳无关**）：
        ① **内容是可解析 `pid`** ⇒ ★ **内核直查该 pid 是否还活着**（`_pid_alive`，fail-closed）
           —— ★ 活 ⇒ **判活、⛔ 不回收**；★ 死 ⇒ **残留 ⇒ 可回收**（★ **自愈仍在，且不必再等 10 s**）；
        ② **内容为空／不可解析**（例：正处在「`O_EXCL` 建出来 → 写 `pid`」之间的**微秒窗口**）
           ⇒ 用★ **本进程的观察窗口**：同一个**内容指纹**被我们**连续观察到 ≥ `TAKE_TOKEN_STALE_SECONDS`**
           ⇒ 判**残留**（★ 活令牌的空窗只持续微秒，一写入 `pid` 就走 ① 的正路）；
        ③ **读不到**（无文件／无权限）⇒ **fail-closed：判活、⛔ 不回收**。
      ★ 另：`pid` 存活 **≠** 令牌一定活（PID 可能被复用）⇒ ② 的窗口**同时兼作**该情形的兜底
        —— ★ 持令牌是**毫秒级**动作，**连续观察到同一个 `pid` ≥ 10 s** 只可能是残留 ✓

    ★ 返回：`True` ⇒ **判活（⛔ 不回收）** ｜ `False` ⇒ **可回收** ✓"""
    try:
        with open(TAKE_TOKEN, "rb") as fh:
            data = fh.read(64)
    except FileNotFoundError:
        _OPAQUE_TOKEN_SEEN.clear()           # ★ 令牌没了 ⇒ 观察窗口清零（下次重建从新起算）
        return True
    except OSError:
        return True                          # ★ ③ fail-closed

    raw = data.decode("ascii", "replace").strip()
    try:
        pid = int(raw)                       # ★ 用 try/except，⛔ 不用 `str.isdigit()`
    except ValueError:                       #   （`'²'.isdigit()` 为 True 而 `int()` 抛 ⇒ 旧写法漏栈，`F-3`）
        pid = None
    if pid is not None and not _pid_alive(pid):
        return False                         # ★ ① 持有者确已死 ⇒ 残留（**无需任何时间戳**）

    now = time.time()                        # ★ ② 观察窗口（**本进程的钟**，与文件时间戳无关）
    for k in [k for k in _OPAQUE_TOKEN_SEEN if k != data]:
        del _OPAQUE_TOKEN_SEEN[k]            # ★ 令牌只有一个名字 ⇒ 只留最新内容指纹
    first = _OPAQUE_TOKEN_SEEN.setdefault(data, now)
    return (now - first) < TAKE_TOKEN_STALE_SECONDS


def _acquire_take_token():
    """★ 取得**接管令牌**（`LOCK.take`）—— 保证**同一时刻只有一个接管者**。
    ★ 令牌通常只被持有**毫秒级**；若进程在持令牌时崩溃 ⇒ 留残留 ⇒ ★ **按<持有者是否还活着>回收**
      （★ T74 修订后**不再看时间戳**——那值会被同名文件**沿用**，见 `_take_token_is_live`）。"""
    try:
        fd = os.open(TAKE_TOKEN, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        os.write(fd, str(os.getpid()).encode("ascii"))
        os.close(fd)
        return True
    except (FileExistsError, PermissionError):
        # ★★ T74 返修（`F-T60-B1`，命中行 `:322`）：Windows 上令牌被**并发清/占**时，
        #    `os.open(..., O_CREAT|O_EXCL)` 抛的是 **`PermissionError(13)`**（文件处于 delete-pending）
        #    而**不是** `FileExistsError` ⇒ 原先漏出 ⇒ 绕过 `LockBusy`/`LockContention` 两分类
        #    ⇒ 上位**裸 traceback**（实测 `N=16`×20 `131/300`；★ 两条腿独立命中同一行）。
        #    ⇒ 与"令牌已存在"**同处**：可清则清（够老才清）、一律按"**未取得**"返回 `False`，⛔ 绝不外泄。
        # ★★ T74 修订（第 2 名 `F-1` · P1）：⛔ **不再用 `getmtime` 判"够老"** —— 该值会被
        #    **同名文件沿用** ⇒ 据此会删掉**活持有者**的令牌 ⇒ 多进程同入接管临界区。
        #    ★ 改判**持有者是否还活着**（见 `_take_token_is_live`）——⛔ 绝不用时间戳。
        if not _take_token_is_live():
            try:
                os.remove(TAKE_TOKEN)
            except OSError:
                pass
        return False


def _release_take_token():
    try:
        os.remove(TAKE_TOKEN)
    except OSError:
        pass


def _sweep_stale_locks():
    """★ T74 返修（`F-T60-B6`）：回收 `<LOCK>.stale.<pid>` 残留 —— 原先**无任何回收路径**。

    ★ 残余成因：接管方崩在 `os.replace(LOCK, dst)` 与 `os.remove(dst)` **之间**
      ⇒ 留下 `<LOCK>.stale.<行凶者 PID>`；★ 该名字**带 PID** ⇒ 后续进程既不认它、也不删它
      ⇒ **永久堆积**（在场件：`_T60_review_B_20261006/_wk5/e2.lock.stale.14560`）。
    ★ 回收判据（**任一**成立即回收）：
        ① 名字里的 PID **已死**（`_pid_alive` 内核直查）；
        ② 文件**够老**（`LOCK_OPAQUE_STALE_SECONDS`）—— ★ ② 专为**兜 PID 复用**：进程死了、
           PID 又被别的进程占用 ⇒ ① 会误判"活"而永不回收。
    ★ ⛔ 只在**持令牌期间**调用 —— 接管临界区是**串行**的 ⇒ 不会误删别的接管者**正在用**的临时名
      （那个名字由持令牌者创建、也由它在同一令牌段内删掉）。
    返回：本次回收的件数。"""
    n = 0
    d = os.path.dirname(LOCK) or "."
    prefix = os.path.basename(LOCK) + ".stale."
    try:
        names = os.listdir(d)
    except OSError:
        return 0
    for name in names:
        if not name.startswith(prefix):
            continue
        p = os.path.join(d, name)
        tail = name[len(prefix):]
        if tail.isascii() and tail.isdigit() and not _pid_alive(int(tail)):
            # ★★ T74 修订（第 2 名 `F-3`）：⛔ 只写 `tail.isdigit()` 会漏 —— `'²'.isdigit()` 为 `True`
            #    而 `int('²')` 抛 `ValueError`；该异常不被 `acquire_lock` 的 `except PermissionError`
            #    捕获、`main()` 又无 `except` ⇒ **重新产生裸栈**（与本卡 `B1` 的修复目标同类）。
            #    ⇒ ★ 先 `isascii()` 再 `isdigit()`（★ 双保险：`int()` 只接受 ASCII 数字）✓
            reclaim = True
        else:
            try:
                reclaim = (time.time() - os.path.getmtime(p)) >= LOCK_OPAQUE_STALE_SECONDS
            except OSError:
                continue
        if reclaim:
            try:
                os.remove(p)
                n += 1
            except OSError:
                pass
    return n


def _try_takeover_and_create():
    """★ **在令牌保护下**完成整段 `[复核 → 搬走陈旧 → 创建]` ⇒ 彻底消除「先判后动」的跨窗口。

    ★★ 为什么必须把**创建**也放进令牌里（`T60` 返修第二次的教训）：若只在"搬走"那一步用令牌，
       会出现 —— **Y 在令牌外读到 `{absent/dead}` ⇒ X 抢在中间创建成功 ⇒ Y 入令牌后
       `os.replace` 把 X 那把<新鲜活锁>搬走 ⇒ Y 再创建 ⇒ 两进程同持**（N=16/32 实测 3–6/20、多持 2）。
       ⇒ 入令牌后**必须<重读>**；且 `[重读 → 搬走 → 创建]` **全程持令牌** ⇒ 与快路径的创建者之间也不可能交叉。
    返回：`'got'` 拿到锁 ｜ `'busy'` 有活持有者（应拒绝）｜ `'opaque'` 不可解析且不够老（应拒绝）｜ `None` 竞争（可重试）。"""
    if not _acquire_take_token():
        return None
    try:
        _sweep_stale_locks()                               # ★ T74（`F-T60-B6`）
        state, pid = _read_lock_owner()
        if state == "alive":
            return "busy"
        if state == "opaque" and not _opaque_lock_is_old():
            return "opaque"
        if state != "absent":
            dst = "%s.stale.%d" % (LOCK, os.getpid())
            try:
                os.replace(LOCK, dst)
            except OSError:
                return None
            try:
                os.remove(dst)
            except OSError:
                pass
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except (FileExistsError, PermissionError):
            # ★ T74（`F-T60-B1` 同形第二处）：锁自身的 `O_CREAT|O_EXCL` 在并发下同样会抛
            #    `PermissionError` —— 语义上与"别人刚建"等价（都＝**这次没建成**）
            #    ⇒ 一并并入，让上层重试（重试会看到活持有者），⛔ 不外泄成裸栈
            return None
        os.write(fd, str(os.getpid()).encode("ascii"))
        os.close(fd)
        return "got"
    finally:
        _release_take_token()


def acquire_lock(max_tries=20):
    """★ 单实例互斥 —— 修本线自造的缺陷（⌛2026-10-03 假红根因）：

    两个 `iso_run` 并发时，**各自灌同一实例、同一库**（`start_iso` 会复用已占用的 8900）
    ⇒ 同一个 `tx_hash` 会被**两个客户端在 1ms 内各打一次**（实测 20:17:43.503/.504）
    ⇒ 双双越过预检 ⇒ 撞 `uk_txhash_role` ⇒ 落败方 `code=7`（而赢家已提交）
    ⇒ 出现「**`code=7` 却 `bill=3`**」这种自相矛盾的**假红**。

    ★★ 版本沿革：
      · `T57` 前（旧法）＝ `exists` 检查 ＋ `open(...,"w")` 覆写 ⇒ **非原子** ⇒ 同步屏障 **20/20 击穿**；
      · `T60` 首版（`AD-03` 方案 A）＝ **`O_CREAT|O_EXCL` 抢锁 ＋ `os.replace` 搬陈旧锁** ⇒ ★ 但留下
        ★★ **`F-T60-A1`「空锁窗口」**（见下），第 1 名复核**加剂量 N=8/N=16** 逮到（N=4 看不见）；
      · ★ **本版（返修）** ＝ 上述 ＋ **`_read_lock_owner()` 的 fail-closed**。

    ★★ **`F-T60-A1` 空锁窗口是什么、为什么 `O_EXCL` 挡不住**：
       `os.open(O_CREAT|O_EXCL)` 建出来的是**空文件**，而"陈旧与否"是**从内容推断**的
       ⇒ 在「**建**」与「**写 PID**」之间那一瞬，失败方读到 `""` ⇒ `"".isdigit()` 假 ⇒ **绕过判活**
       ⇒ 直落陈旧分支 ⇒ `os.replace` **把刚建好、还没写 PID 的<活锁>搬走** ⇒ ★ **两进程同持**。
       ⇒ 修法：★ **空／不可解析 ⇒ 一律视为<活锁>（fail-closed，⛔ 不接管）**，
         仅当它**够老**（`LOCK_OPAQUE_STALE_SECONDS`）才按陈旧接管 ⇒ **两进程同持被消除**，**自愈仍在**。
       ★ 为什么不用 "tmp + `os.link`"（复核建议之一）：★ **本机 `E:` 卷是 exFAT，`os.link` 不支持**
         （实测 `OSError [WinError 1]`），`os.replace` 又会**覆盖**（不满足"不存在才建"）
         ⇒ 在**本文件系统上**「创建即带内容」不可行 ⇒ 取**等价**的 fail-closed 路线（效果由 `V1` 证）。

    ★★ **返修第三次（本版）**：**取消"未取令牌的快路径"** —— 所有获取**一律经令牌** `[复核 → 搬走陈旧 → 创建]`。
       理由（N=32 实测）：若保留快路径，**它不需要令牌**，于是能在"接管者刚把陈旧锁搬走、还没创建"的
       那一瞬抢建 ⇒ 与接管者交叉 ⇒ 仍有 3–5/20 多持（多持 ≤3）。★ 全部串行化后，**同一时刻只有一个进程
       处在获取临界区**，而它在令牌内**重读并复核**（内核级探活，实测零误判）⇒ **活持有者永不被搬走**。

    ★★ **返修第四次（T74 · 本版）**：只动**可诊断性**，⛔ 不动互斥核（承 `F-T60-B1`/`B2`/`B3`/`B6` ＋ `R1`）：
      · `B1` 两处 `O_CREAT|O_EXCL` 的 `PermissionError` 并入"未取得" ＋ 本函数再兜一层 ⇒ **出口只余两类**；
      · `B2`／`R1` **重试加退避**（累计 ≥ `TAKE_TOKEN_STALE_SECONDS`）⇒ 归因回 `LockBusy`、残留令牌能自愈；
      · `B3` 用户可见的等待时长按 `+MTIME_GRANULARITY_SLACK_SECONDS` 计（exFAT 的 2 s 粒度）；
      · `B6` 持令牌期间回收 `<LOCK>.stale.<pid>`。
    """
    for i in range(max_tries):
        # ★★ 一律走令牌段（⛔ 无快路径）：复核 → 搬走陈旧 → 创建
        try:
            r = _try_takeover_and_create()
        except PermissionError:
            # ★ T74（`F-T60-B1` 兜底）：并发清/占下的权限争用已在两处 `O_CREAT|O_EXCL` 并入
            #    "未取得"；此处再兜一层 ⇒ ★ **`acquire_lock` 的出口只余 `LockBusy`/`LockContention`**，
            #    ⛔ 不会有裸栈逃到 `main()`（`main` 只有 `finally`、**没有** `except`）。
            r = None
        if r == "got":
            return
        if r == "busy":
            raise LockBusy(
                "★ 拒绝并发：已有 iso_run 在跑 —— 同一实例/同一库会互撞幂等键，产生假红")
        if r == "opaque":
            raise LockBusy(
                "★ 拒绝并发：锁文件内容不可解析（按 fail-closed 视为活锁，⛔ 不接管）"
                f" —— 若确认无人持有，等 {LOCK_OPAQUE_STALE_SECONDS + MTIME_GRANULARITY_SLACK_SECONDS}s 后再试")
        # r is None ⇒ 令牌被别人持着／常规竞争 ⇒ ★ 退避后重试（★ T74，见下）
        if i < max_tries - 1:
            time.sleep(min(0.05 * (2 ** i), 1.0))
    raise LockContention(
        "★ 锁竞争：重试 %d 次仍失败（疑似多条线同时抢）"
        " —— 另一种成因是**接管令牌残留**（进程恰在持令牌的微秒窗口里崩溃）；"
        "本机 `E:` 卷是 exFAT、mtime 粒度为 2 s ⇒ 令牌标称 %d s、**实际自愈需 %d–%d s**"
        % (max_tries, TAKE_TOKEN_STALE_SECONDS,
           TAKE_TOKEN_STALE_SECONDS, TAKE_TOKEN_STALE_SECONDS + MTIME_GRANULARITY_SLACK_SECONDS))


def release_lock():
    """★ T60 返修（`F-T60-A2`）：**复核身份再删** —— 只在锁内容**就是本进程 PID** 时删；
    ⛔ 不会误删别人的锁（若本进程已不是持有者 ⇒ 不动）。"""
    try:
        if not os.path.exists(LOCK):
            return
        old = open(LOCK, encoding="utf-8", errors="replace").read().strip()
        if old == str(os.getpid()):
            os.remove(LOCK)
    except OSError:
        pass


# ---------- 主流程 ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-stop", action="store_true", help="跑完保留实例 B")
    ap.add_argument("--keep-seed", action="store_true", help="不重新播种")
    a = ap.parse_args()

    print("=== T29 隔离运行（(乙-1)：第二实例 + 第二库）===")
    print(f"  ★ 连接目标：判据 DB={DST_DB}  API={ISO_API}   ｜ 护栏 DB={SRC_DB}")
    print("  ★ 共享 8888 **未触碰**（只起停 8900）")

    r = {"start": False, "seed": False, "guard": False, "suite": {}}
    acquired = False                       # ★ 只有**真的拿到锁**才允许停实例/放锁
    try:
        acquire_lock()
        acquired = True
        start_iso()
        ok, body = wait_health()
        r["start"] = ok
        print(f"  [health] {ISO_API}/health ⇒ {body[:100] if ok else body}")
        if not ok:
            print("★ 实例 B 未就绪 ⇒ 终止"); return 2

        if not a.keep_seed:
            # ★★ 顺序要点：**schema 克隆必须在实例启动之后** —— 启动期的 AutoMigrate
            #    （`DefaultStringSize:191`）会把克隆来的 `varchar(32)` 又加宽成 `varchar(191)`，
            #    保真度当场丢失（本线实测）。故：先 start（让它 AutoMigrate 一遍）→ 再克隆 → 再种行。
            r["seed"] = True
            for tag, argv in (("schema", ["--schema-only"]), ("rows", [])):
                print("  [seed/%s] %s" % (tag, "克隆业务库结构" if tag == "schema"
                                          else "播种判据夹具（⛔ 不种 bill）"))
                sp = subprocess.run([sys.executable, os.path.join(FW, "seed_test_db.py"), *argv],
                                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                                    env={**os.environ, "DSH_DB": DST_DB, "DSH_SEED_FROM": SRC_DB})
                for l in (sp.stdout or "").strip().splitlines():
                    print("    " + l)
                if sp.returncode != 0:
                    r["seed"] = False

        before = db_snapshot("before")
        rbefore = redis_snapshot("before")
        env = {**os.environ, "DSH_DB": DST_DB, "DSH_API": ISO_API}
        # ★ F-08（复核 finding）：**两态在同一次运行内跑完** —— 置绑定 → 跑 → 置解绑 → 跑 → 复位。
        #   · 只动**隔离库** `qk_e2e_test`（⛔ 从不碰业务库）；
        #   · 夹具翻转放在**运行器层**（判据内部仍"只读夹具态"，保持纯断言语义 —— 裁定明令）。
        seed_cuid = fixture_cuid()
        other_cuid = 0 if seed_cuid != 0 else 201
        states = [(f"state1_cuid{seed_cuid}", seed_cuid), (f"state2_cuid{other_cuid}", other_cuid)]
        try:
            for state, cuid in states:
                set_fixture_cuid(cuid)
                print(f"  [state] ==== {state}（{DST_DB}.packet.custom_user_id={cuid}）====")
                for s in SUITE:
                    p = subprocess.run([sys.executable, os.path.join(FW, s)], capture_output=True,
                                       text=True, encoding="utf-8", errors="replace", env=env)
                    lines = (p.stdout or "").splitlines()
                    tail = [l for l in lines if l.startswith("RESULT=")]
                    key = f"{state}/{s}"
                    r["suite"][key] = (p.returncode, tail[-1] if tail else "(无 RESULT 行)")
                    print(f"  [suite] {key}: EXIT={p.returncode}  {r['suite'][key][1]}")
                    for l in lines:                  # ★ 失败明细随行打印（免二次复跑）
                        if l.startswith("  - ") or l.startswith("RESULT=RED"):
                            print(f"          {l.strip()}")
                    with open(os.path.join(FW, "_iso_last_%s_%s.log" % (state, s.replace(".py", ""))),
                              "w", encoding="utf-8") as fh:
                        fh.write(p.stdout or "")
        finally:
            # ★ 复位到播种态（成败都复位）—— 否则下次运行的"播种态"已被改掉
            set_fixture_cuid(seed_cuid)
            print(f"  [state] 已复位 {DST_DB}.packet.custom_user_id={seed_cuid}")
        after = db_snapshot("after")
        rafter = redis_snapshot("after")
        bad = db_diff(before, after) + redis_diff(rbefore, rafter)
        r["guard"] = (len(bad) == 0)
        if bad:
            print("  ★★ 报警：共享设施被改动 —— " + "；".join(bad))
        else:
            print("  ✓ 护栏：业务库 8 张表**行数与内容哈希全未变**（MySQL 隔离有效）"
                  f" ＋ 主栈 Redis db{GUARD_REDIS_DB} **键数与键名哈希全未变**（Redis 已隔离到 db1）")
    finally:
        if acquired and not a.no_stop:
            stop_iso()
        if acquired:
            release_lock()

    print("\n=== 结论 ===")
    print(f"  实例 B 起：{'OK' if r['start'] else 'FAIL'} · 播种：{'OK' if r['seed'] else 'FAIL'}"
          f" · 护栏(业务库未动)：{'OK' if r['guard'] else 'FAIL'}")
    for s, (rc, line) in r["suite"].items():
        print(f"  {s}: EXIT={rc} {line}")
    allok = r["start"] and r["seed"] and r["guard"] and all(rc == 0 for rc, _ in r["suite"].values())
    print("ISO_RUN=" + ("OK" if allok else "BAD"))
    return 0 if allok else 1


if __name__ == "__main__":
    _sys.exit(main())
