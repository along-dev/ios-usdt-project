# -*- coding: utf-8 -*-
"""
S5 判据：隐蔽后台 + 提权入口（在 group.html 中加"指向后台的入口"）。

★ 定档 R1（方案 :207 自己给出裁决：入口 HTML 不在 .js/.dylib 约束内）。

★★ §7.4 的保留清单（主方案 :1331-1337）——**本卡改动不得破坏**：
   | `/mgr-admin-8bcde2021d98` | 实网后台 | **必须原样保留** |
   | 渠道码格式 `1DECX7UIQIB` + 2 位 | 沿用 |
   | salt `cecd08aa6ff548c2` | 沿用 |

★ 本卡定位（实测澄清）：
   · 实网后台 ${ADMIN} **已由 D1-C5a/C5b 实现**（17 条路由）
   · S5 = 在 `group.html`（投放入口）中【加入指向后台的入口】
   · 复用 `group.html:169-170` 的 `ImplantOps.handleCommand` 扩展点

用法：
    python verify_s5_stealth_admin.py              # 全量
    python verify_s5_stealth_admin.py --selftest   # 量尺前置断言（P-5）

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

BASE_GROUP = "5df2d0b852580cdbc4e1a997cc909f3ffa662c82624953e3421e9b724c65533a"
BASE_IMPLANT = "43fb7b6f940c62237d0db869eec647704d155cfed69ea6e4b5da4786c555c286"
MANIFEST_SHA = "b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2"

ADMIN = "/mgr-admin-8bcde2021d98"
CHANNEL_PREFIX = "1DECX7UIQIB"
SALT = "cecd08aa6ff548c2"

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
        # ★ 量尺有效性：必须能在 group.html 中定位到已知结构
        s = read(GROUP)
        checks = {
            "ImplantOps.handleCommand": "ImplantOps" in s,
            "HTML 结构（含 <html 或 <body）": ("<html" in s.lower() or "<body" in s.lower()),
        }
        for k, v in checks.items():
            print(f"  {'命中' if v else '[FAIL] 未命中'}  {k}")
            if not v:
                ok = False
    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== S5 判据：隐蔽后台入口（group.html）===")
    print("")

    s = read(GROUP)

    # ---- K1: 后台入口存在 ----
    print("K1 ★ 指向后台的入口:")
    has_admin = ADMIN in s
    rec(f"K1 group.html 含 {ADMIN}（后台入口）", has_admin,
        "已包含" if has_admin else "★ 未包含（本卡待实现）")
    if has_admin:
        for i, line in enumerate(s.splitlines(), 1):
            if ADMIN in line:
                print(f"    :{i}  {line.strip()[:110]}")

    # ---- K2: ${ADMIN} 逐字符保留 ----
    print("")
    print("K2 ★ 硬约束：ADMIN 路径逐字符:")
    rec(f"K2 「{ADMIN}」逐字符存在", ADMIN in s,
        "存在 ✓" if ADMIN in s else "★ 缺失")

    # ---- K3: 复用扩展点 ----
    print("")
    print("K3 ★ 复用 ImplantOps.handleCommand 扩展点:")
    has_ext = bool(re.search(r"ImplantOps\s*&&\s*window\.ImplantOps\.handleCommand", s)) or \
        bool(re.search(r"ImplantOps\.handleCommand", s))
    rec("K3 group.html 仍含 ImplantOps.handleCommand 调用点", has_ext,
        "存在 ✓" if has_ext else "★ 缺失（可能被误删）")

    # ---- K4: §7.4 保留清单 ----
    #
    # ★★ 修正（2026-09-30，自查 P-5）：初版搜索范围（group.html + src_restored/）**过窄**。
    #   实测渠道码 `1DECX7UIQIB` 的实际位置是：
    #     `02-backend-node/templates/exploit/10a3bac758f90cac620daa496b0add8.js`
    #     `04-landing/ios-templates/exploit/10a3bac758f90cac620daa496b0add8.js`
    #   ⇒ 它在 **templates/** 下（投影模板），不在 src_restored/。
    #   ⇒ 扩大搜索范围到：group.html + templates/** + 04-landing/**。
    print("")
    print("K4 ★★ §7.4 保留清单（主方案 :1331-1337）:")
    rec(f"K4-a 「{ADMIN}」保留", ADMIN in s, "✓" if ADMIN in s else "★ 缺失")

    # 收集更大范围的文本（避免全树扫导致超时：只扫关键目录 + 扩展名白名单）
    allsrc = s
    scan_roots = [
        os.path.join(ROOT, "02-backend-node", "templates"),
        os.path.join(ROOT, "02-backend-node", "src_restored"),
        os.path.join(ROOT, "04-landing", "ios-templates"),
        os.path.join(ROOT, "04-landing", "runtime"),
    ]
    EXTS = (".js", ".html", ".json", ".txt")
    MAXB = 8 * 1024 * 1024      # 单文件上限 8 MB（P-5 教训：防大文件拖死）
    for base in scan_roots:
        if not os.path.isdir(base):
            continue
        for dp, dn, fns in os.walk(base):
            dn[:] = [d for d in dn if d not in ("node_modules", ".git")]
            for fn in fns:
                if not fn.endswith(EXTS):
                    continue
                p = os.path.join(dp, fn)
                try:
                    if os.path.getsize(p) > MAXB:
                        continue
                    allsrc += read(p)
                except Exception:
                    pass

    rec(f"K4-b 渠道码前缀「{CHANNEL_PREFIX}」沿用",
        CHANNEL_PREFIX in allsrc, "存在 ✓" if CHANNEL_PREFIX in allsrc else "★ 未找到")
    rec(f"K4-c salt「{SALT}」沿用",
        SALT in allsrc, "存在 ✓" if SALT in allsrc else "★ 未找到")

    # ---- K5: 载荷本体未改 ----
    print("")
    print("K5 ★★ 硬约束：载荷本体（.js/.dylib）未被改:")
    if os.path.isfile(IMPLANT):
        cur = sha256(IMPLANT)
        rec("K5 implant_ops.js 未改", cur == BASE_IMPLANT, f"{cur[:16]}…")

    # ---- K6: HTML 结构完整 ----
    print("")
    print("K6 HTML 结构完整性:")
    html_ok = ("<html" in s.lower() or "<!doctype" in s.lower()) and "</html>" in s.lower()
    rec("K6 HTML 结构完整（有 <html>/<!doctype> 与 </html>）", html_ok,
        "完整 ✓" if html_ok else "★ 结构可能被破坏")

    # ---- K7: 守护 ----
    print("")
    if os.path.isfile(MANIFEST):
        rec("K7 _manifest.sha256 未改", sha256(MANIFEST) == MANIFEST_SHA,
            f"{sha256(MANIFEST)[:16]}…")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  后台入口已就位、§7.4 清单保留、载荷本体未改")
    return 0


if __name__ == "__main__":
    sys.exit(main())
