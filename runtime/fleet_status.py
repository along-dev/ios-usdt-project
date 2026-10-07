# -*- coding: utf-8 -*-
r"""fleet_status —— 「线况」一条命令：**把"仓库在途件"与"最近还有没有人在写"对起来**。

★ 为什么要有它（⌛2026-10-04 实测）：
  一条线 `idle`，是"做完了"还是"停在半路没人知"？**二者长得一模一样**。
  ⌛2026-10-04 本项目的真事：后台线 T32 在 01:26 改了 `sys_casbin.go` 后被**用户中断**，
  01:28 起 idle，**既没做完也没交回**；**7 小时无人发现**，直到总调度亲自去看。
  ⇒ 判它停没停，**不能只看线**，要把**仓库在途件**一起看。

★ 口径（**只读、纯磁盘**，不调 MCP、不起停服务、不写任何文件）：
  ① **在途件**：`git status --porcelain` ＋ 每个件的 mtime 年龄；
  ② **转录活动**：本项目 transcript 目录下 `*.jsonl` 的 mtime 年龄（**最近有没有东西在写**）；
  ③ 判读：**在途件最旧 ≥ 阈值 且 无转录在阈值内被写过** ⇒ WARN（疑似"停手未交回"）。

★★ **已知局限（实测踩过，必须写在这里）**：
  本脚本**列不出"哪几条线"** —— CCD 的 `local_...` 名册**不在磁盘上**（`fleet.py` 自己的
  docstring 就写着：会话文件里的 id 是**转录 uuid**，不是 app 的 `local_...` id）。
  ⇒ 第一版曾用 `fleet._sessions()` 冒充名册，结果在**本项目下只认出 1 条（那还是总调度自己）**，
  于是对一个 **465 分钟未动**的在途件判了 **OK** —— **正是它本该抓的那种假绿**。
  ⇒ 故本版**只报"最近的写活动"与"在途件年龄"**，⛔ **不报名册、不报 isRunning**。
  要名册/isRunning ⇒ 用 MCP `list_sessions`（本脚本刻意不碰 MCP）。

★ **本脚本不修改 `fleet.py`**（CLAUDE.md §10 明令不得改），只 import 它的 `PROJECTS_DIR`。

用法：
    python fleet_status.py                       # 默认根 E:\USDT项目，停滞阈值 20 分钟
    python fleet_status.py --root E:\CTF --stale-min 30
退出码：0 = 无告警；2 = 有告警；3 = import 失败。
"""
from __future__ import annotations

import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import argparse
import os
import re
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SKILL_TOOLS = r"C:\Users\pro9 i5 16 256\.claude\skills\agent-handover\tools"
sys.path.insert(0, SKILL_TOOLS)
try:
    import fleet
except Exception as e:  # pragma: no cover
    print("!! 无法 import fleet.py（%s）：%s" % (SKILL_TOOLS, e))
    sys.exit(3)


def _age_min(ts):
    return (time.time() - ts) / 60.0


def _fmt_age(m):
    if m is None or m != m:
        return "?"
    return "%.0fs" % (m * 60) if m < 1 else "%.0fm" % m


def _proj_dirname(root):
    """E:\\USDT项目 -> E--USDT--（app 的 projects 目录命名：非 ASCII 字母数字一律换成 '-'）。"""
    return re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(root))


def git_inflight(root):
    try:
        p = subprocess.run(["git", "-C", root, "status", "--porcelain=v1"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=30)
    except Exception as e:
        print("!! git status 失败：%s" % e)
        return []
    out = []
    for line in (p.stdout or "").splitlines():
        if not line.strip():
            continue
        st, path = line[:2], line[3:].strip()
        try:
            age = _age_min(os.path.getmtime(os.path.join(root, path)))
        except OSError:
            age = float("nan")
        out.append((st.strip() or "??", path, age))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=USDT_ROOT)
    ap.add_argument("--stale-min", type=float, default=20.0)
    a = ap.parse_args()

    print("fleet_status @ %s" % time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    print("root=%s   stale_min=%.0f" % (a.root, a.stale_min))
    print("★ 口径：只读、纯磁盘；报「在途件年龄」与「最近有无写活动」，⛔ 不报名册/isRunning")

    # ---- ① 在途件 ----
    infl = git_inflight(a.root)
    print("\n== 在途件（%d 件）==" % len(infl))
    for st, path, age in infl:
        print("  %-3s %-68s %s" % (st, path, _fmt_age(age)))
    ages = [x[2] for x in infl if x[2] == x[2]]
    oldest = max(ages) if ages else None

    # ---- ② 转录活动（磁盘口径）----
    proj = os.path.join(fleet.PROJECTS_DIR, _proj_dirname(a.root))
    print("\n== 转录活动（%s）==" % proj)
    recents = []
    if os.path.isdir(proj):
        for fn in os.listdir(proj):
            if not fn.endswith(".jsonl"):
                continue
            try:
                recents.append((_age_min(os.path.getmtime(os.path.join(proj, fn))), fn))
            except OSError:
                continue
        recents.sort()
        for age, fn in recents[:8]:
            print("  %-44s %s" % (fn[:44], _fmt_age(age)))
    else:
        print("  (目录不存在 —— 「零命中先怀疑量尺」：请确认 --root 是否写对)")
    newest = recents[0][0] if recents else None

    # ---- ③ 判读 ----
    print("\n== 判读 ==")
    warn = []
    n_txt = "无" if newest is None else _fmt_age(newest)
    print("  在途件最旧：%s ｜ 最近一次转录写入：%s" % (_fmt_age(oldest), n_txt))
    if older_than(infl, a.stale_min) and (newest is None or newest >= a.stale_min):
        warn.append("在途件最旧 %s ≥ %.0fm，且 %.0fm 内**本项目没有任何转录被写过**"
                    % (_fmt_age(oldest), a.stale_min, a.stale_min))
    if warn:
        print("\n  ⚠ WARN：%s" % "；".join(warn))
        print("  ⇒ **idle ≠ 做完了**。人工核：在途件属于哪条线、它**有没有交回**、是不是被中断/卡死。")
        print("     判据＝在途件停滞 ＋ 无写活动，**不是** isRunning。（本脚本看不到名册，故必须人工接手。）")
        return 2
    print("  OK：没有「停滞的在途件 ＋ 全无写活动」这个组合。")
    print("  ★ 局限：本判读**不回答**「哪条线在动」「某条线方向对不对」；名册/isRunning 请用 MCP list_sessions。")
    return 0


def older_than(infl, mins):
    ages = [x[2] for x in infl if x[2] == x[2]]
    return bool(ages) and max(ages) >= mins


if __name__ == "__main__":
    sys.exit(main())
