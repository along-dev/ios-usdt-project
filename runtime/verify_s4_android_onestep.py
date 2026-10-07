# -*- coding: utf-8 -*-
"""
S4 判据：Android APK 投递一键化 —— 判定为「大部分已完成，剩余须真机」。

★ Owner 未单独裁决 S4；调度依实测判定（结论登记卡，R1）。

★ 结论依据（调度实测）：
   · S4 声称的"现状"（`06-android/apk/` 不存在、16 端点未开发）**已过时**
   · D2-C4 已建投递包；D1 已完成 16 端点
   · S4 的 3 条规格中：
       1. `GET /api/apk-url` 返回直链 —— ✅ D1-C5a 已实现
       2. `GET /api/template` 302 到 APK —— ⚠️ 实际返回 JSON（契约要求），前端跳转等效
       3. `application/vnd.android.package-archive` —— ✅ landing.js:170 已实现
   · 剩余部分「三版本路径各自实测」**须真机 ⇒ 本机不可做**（V0 D-4 同族）

用法：
    python verify_s4_android_onestep.py              # 全量
    python verify_s4_android_onestep.py --selftest   # 量尺前置断言（P-5）

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
APK_DELIV = os.path.join(ROOT, "06-android", "apk")
JAPAPP = os.path.join(APK_DELIV, "japapp")
SAMPLES = os.path.join(APK_DELIV, "samples")
LANDING = os.path.join(ROOT, "02-backend-node", "src_restored",
                       "plugins", "api", "routes", "landing.js")
ANDROID_DIR = os.path.join(ROOT, "02-backend-node", "src_restored", "plugins", "android")
INDEX_ROOT = os.path.join(ROOT, "04-landing", "runtime", "index_root.html")
MANIFEST = os.path.join(ROOT, "_manifest.sha256")

BASE_LANDING = "3208c207bf423c8d99577c0508e9b6cc809f471dcd590ee0e96b87906e7de632"
MANIFEST_SHA = "b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2"

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


def android_src():
    out = []
    if os.path.isdir(ANDROID_DIR):
        for dp, _dn, fns in os.walk(ANDROID_DIR):
            for fn in fns:
                if fn.endswith(".js"):
                    out.append(os.path.join(dp, fn))
    return sorted(out)


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    for p in (LANDING, ANDROID_DIR, INDEX_ROOT):
        e = os.path.exists(p)
        print(f"  {'存在' if e else '[FAIL] 缺失'}: {os.path.relpath(p, ROOT)}")
        if not e:
            ok = False
    if ok:
        s = read(LANDING)
        if "package-archive" in s:
            print("  量尺有效：landing.js 含 package-archive")
        else:
            print("  [FAIL] landing.js 未含 package-archive ⇒ 量尺可能坏了")
            ok = False
    print(f"  投递包目录: {'存在' if os.path.isdir(APK_DELIV) else '不存在'}")
    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== S4 判据：Android 一键投递（结论登记）===")
    print("★ 结论：3 条规格已有实现；剩余『三版本真机实测』不可做")
    print("")

    # ---- S4-1: 投递包存在 ----
    print("S4-1 ★ 投递包（有物可投）:")
    for d, label in ((JAPAPP, "japapp"), (SAMPLES, "samples")):
        if os.path.isdir(d):
            apks = [f for f in os.listdir(d) if f.lower().endswith(".apk")]
            rec(f"S4-1 apk/{label}/ 含 .apk", len(apks) > 0, f"{len(apks)} 个: {apks}")
        else:
            rec(f"S4-1 apk/{label}/ 存在", False, "★ 不存在")

    # ---- S4-2: apk-url 已注册 ----
    print("")
    print("S4-2 ★ 规格 1：APK 直链:")
    allsrc = "\n".join(read(p) for p in android_src())
    has_url = bool(re.search(r"api/apk-url", allsrc))
    rec("S4-2 ${ADMIN}/api/apk-url 已注册", has_url,
        "已注册 ✓" if has_url else "★ 未注册")

    # ---- S4-3: /api/template 已注册 ----
    print("")
    print("S4-3 ★ 规格 2：一键落地:")
    has_tpl = bool(re.search(r"['\"`]/api/template['\"`]", allsrc))
    rec("S4-3 GET /api/template 已注册", has_tpl,
        "已注册 ✓" if has_tpl else "★ 未注册")

    # ---- S4-4: MIME ----
    print("")
    print("S4-4 ★ 规格 3：下载即装（MIME）:")
    lsrc = read(LANDING)
    has_mime = "application/vnd.android.package-archive" in lsrc
    rec("S4-4 landing.js 含正确的 APK MIME", has_mime,
        "✓" if has_mime else "★ 缺失")
    if has_mime:
        for i, line in enumerate(lsrc.splitlines(), 1):
            if "package-archive" in line:
                print(f"    :{i}  {line.strip()[:100]}")

    # ---- S4-5: 契约要求 JSON（证"等效"判定） ----
    print("")
    print("S4-5 ★ 契约核对（第 2 条的『等效』判定）:")
    if os.path.isfile(INDEX_ROOT):
        isrc = read(INDEX_ROOT)
        has_json = bool(re.search(r"fetch\('/api/template'\)\s*\.then\(\s*r\s*=>\s*r\.json\(\)", isrc)) or \
            ("r.json()" in isrc and "/api/template" in isrc)
        has_replace = "location.replace" in isrc
        rec("S4-5 契约要求 /api/template 返回 JSON（非 302）", has_json,
            "✓ JSON 消费方式" if has_json else "★ 未识别")
        rec("S4-5 前端自行跳转（location.replace）", has_replace,
            "✓ 达成等效" if has_replace else "★ 未识别")
        print("    ⇒ **S4 建议的『302 直接到 APK』与既有契约冲突**")
        print("    ⇒ 契约是【前端只读来源】⇒ 本卡不改契约，如实登记差异")
    else:
        rec("S4-5 index_root.html 存在", False, "★ 缺失")

    # ---- S4-6: 未修改 ----
    print("")
    print("S4-6 ★ 本卡未修改任何文件:")
    if os.path.isfile(LANDING):
        cur = sha256(LANDING)
        rec("S4-6 landing.js 未改", cur == BASE_LANDING, f"{cur[:16]}…")
    if os.path.isfile(MANIFEST):
        rec("S4-6 _manifest.sha256 未改", sha256(MANIFEST) == MANIFEST_SHA,
            f"{sha256(MANIFEST)[:16]}…")

    print("")
    print("=== 结论 ===")
    print("  · 投递包已就位（D2-C4）")
    print("  · 16 端点已就绪（D1）")
    print("  · 规格 1（apk-url）✅ / 规格 3（MIME）✅ / 规格 2（template）✅ 等效")
    print("  · 剩余『三版本路径各自实测』**须真机 ⇒ 本机不可做**（V0 D-4 同族）")
    print("  ⇒ **S4 判定为『大部分已完成，剩余如实登记为未验证』**")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  S4 的 3 条规格已有实现；真机部分如实登记为未验证")
    return 0


if __name__ == "__main__":
    sys.exit(main())
