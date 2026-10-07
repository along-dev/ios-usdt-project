# AD-03 方案件 —— `iso_run.py` 的**互斥锁是坏锁**（TOCTOU）：改法与代价

> **编号**：`AD-03`（承 `09-docs/ARCHITECTURE.md` §十二 架构债登记表）｜ **性质**：**只出件，⛔ 不落码**
> **件**：`E:\ios漏洞\_integration\_fix_work\iso_run.py`（**树外**，不在本仓 git 内）
> **产件**：后台线（接班人 `local_96adb6ae`）｜ **时刻**：⌛2026-10-04
> **★ 该件现处「冻结」状态** —— 改动走批次（与 `T31 §五` 的 F-10 同批更省）

---

## 一 · 缺陷（**实读原文，非转述**）

`iso_run.py:239-256`（现行）：

```python
def acquire_lock():
    if os.path.exists(LOCK):                       # ← ① 先"看"
        old = open(LOCK, encoding="utf-8").read().strip()
        if old.isdigit() and _pid_alive(int(old)):
            raise RuntimeError("★ 拒绝并发：已有 iso_run 在跑（PID %s）…" % old)
        try:
            os.remove(LOCK)                        # ← ② 陈旧才"删"
        except OSError:
            pass
    with open(LOCK, "w", encoding="utf-8") as fh:  # ← ③ 再"建"（**非原子**）
        fh.write(str(os.getpid()))
```

**TOCTOU 窗口**：`③` **不是**原子创建。两个进程可**同时**走到 `①`（都发现没有锁，或都发现陈旧锁），
**双双** `os.remove`、**双双** `open(...,"w")` 覆写 ⇒ **两个都认为自己持锁 ⇒ 双双继续跑**
⇒ 正是 `T30 §十` 那次假红的成因（两个 `iso_run` 各自灌同一实例、同一库）。

★ **本项目已自认**：同步屏障下 **20/20 次击穿**。
★ **但要注意**：它**不是**"锁写错了"这么单一 —— `_pid_alive` 也踩过一个坑（`E-360`：`tasklist` 无匹配时把 `INFO:` 打到 stdout ⇒ 任何 PID 都算存活）。**两个缺陷叠在一起**：一个有窗口、一个会把死锁认成活锁。

## 二 · 替换方案（**推荐 A**）

### 方案 A ★ 推荐：`O_CREAT|O_EXCL` 原子创建 ＋ 原子"搬走陈旧锁"

```python
LOCK = os.path.join(FW, "_iso_run.lock")

def _takeover_stale_lock():
    """把**陈旧**锁原子搬走（`os.replace` 是原子且**目标唯一**⇒ 只有一个进程搬得动）。"""
    dst = "%s.stale.%d" % (LOCK, os.getpid())
    try:
        os.replace(LOCK, dst)          # ⛔ 不用 os.remove + open：那正是漏洞
    except OSError:
        return False                   # 别人刚搬走／刚建了新锁 ⇒ 让对方赢
    try:
        os.remove(dst)
    except OSError:
        pass
    return True

def acquire_lock(max_tries=3):
    for _ in range(max_tries):
        try:
            # ★ 原子：O_CREAT|O_EXCL —— "不存在则创建"，内核保证只有一个赢家
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            old = open(LOCK, encoding="utf-8").read().strip()
            if old.isdigit() and _pid_alive(int(old)):
                raise RuntimeError("★ 拒绝并发：已有 iso_run 在跑（PID %s）…" % old)
            _takeover_stale_lock()     # 陈旧 ⇒ 原子搬走；搬不动 ⇒ 重试
            continue
        os.write(fd, str(os.getpid()).encode("ascii"))
        os.close(fd)
        return
    raise RuntimeError("锁竞争：重试 %d 次仍失败（疑似多条线同时抢）" % max_tries)
```

**为什么这样就对了**：
1. `O_CREAT|O_EXCL` 是**内核级原子**的"不存在则创建" ⇒ **不存在**两方同时"创建成功"的窗口；
2. 陈旧锁的接管用 **`os.replace`（原子改名）**，不是"读→删" ⇒ **只有一个进程搬得动**，搬不动的那个重试即可；
3. 死锁自愈**保留**（`_pid_alive` 判死）。
★ **`release_lock()` 无需改**（它只在 `old == str(os.getpid())` 时删 ⇒ 不会误删别人的锁）。

### 方案 B：Windows 命名互斥体（`CreateMutexW`）
`ctypes` 调 `CreateMutexW(None, False, "Global\\usdt_iso_run")` ＋ `WaitForSingleObject(0)` ⇒ **内核对象**，天然原子、**进程崩溃自动释放**（连"陈旧锁"这一整类问题都消失）。
**代价**：要 `ctypes` 直调 Win32（本机 `windows-portable-pitfalls` 有同类先例）、**跨平台不可移植**（但本工具本来就在 Windows 跑）。
⇒ **若能接受 Win 专用，B 比 A 更彻底**（A 仍需"判死 + 接管"两步，B 由内核兜）。**建议 A**（改动小、可读、不引 ctypes），**B 列为备选**。

### 不推荐：加"重试/睡一会儿"
只把窗口变窄，**不消除**。本项目已实测"同步屏障下 20/20 击穿" ⇒ 靠时序缓解无效。

## 三 · 改动代价（**冻结件**）

| 项 | 评估 |
|---|---|
| **改哪些行** | **只有 `acquire_lock`（约 `:239-256`）**；新增一个约 10 行的 `_takeover_stale_lock`；`LOCK` 常量不动；`release_lock` **不动** |
| **对已验锚的影响** | ★ **`iso_run.py` 的 sha 会变** ⇒ 凡引用其旧 sha 的件（`T29 §七/§九`、`复核输入包`、`T27-V2负控补做` 的 §1 锚表）**都会过期** ⇒ **须同批一并更正那些锚**（这正是「冻结件不做顺手修」要防的 churn） |
| **功能风险** | 低：锁**更严**（原来会放过并发，现在会真拒）⇒ 可能**暴露**此前被掩盖的并发调用（那是**好事**，但需在件里写明） |
| **验证方式（可机检）** | 起 **N 个进程同时** `acquire_lock()` ⇒ **断言恰 1 个成功、其余抛"拒绝并发"**；再**伪造一个死 PID 的锁** ⇒ 断言**能接管**（`E-360` 同法）。★ 两条都要给读数 |
| **与 F-10 的关系** | `T31 §五` 的 **F-10** 就是这条 ⇒ **同批改最省**（一次动它、一次更正锚） |

## 四 · 未能验证

1. **未实测**：本件**只读**，⛔ 没改 `iso_run.py`、⛔ 没跑任何并发实验 ⇒ §二 的两条验证**都还没读数**；
2. **未证**"20/20 击穿"这个数 —— 那是**上游件自述**，我**未复跑**；
3. **方案 B 未验证**：`ctypes` 调 `CreateMutexW` 的可行性、以及**本机是否有"全局命名对象权限"**（受限账户下 `Global\` 可能建不了）**未测**；
4. **未盘**：除 `iso_run.py` 外**是否还有别的锁**用了同一坏形态（如 `_fix_work/` 其它脚本）—— 本件**只查了 `iso_run.py`**，「全仓坏锁扫查」**未做**（可作为本件的后续小项）。
