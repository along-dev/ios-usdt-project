# -*- coding: utf-8 -*-
"""
D2-C1b 判据：钉住 @vitejs/plugin-vue 版本，修复构建互斥。

★ 缺陷（D2-C1 实测 + 调度复核）：
   package.json:34  "@vitejs/plugin-vue": "latest"   → 今日解析 6.0.9（peer vite ^5+）
   package.json:48  "vite": "^2.8.0"                 → 实装 2.9.18（无 createFilter 导出）
   ⇒ npm install ERESOLVE；vite build 崩在配置加载阶段（src/ 从未执行）。

★ 修复：L34 → "^2.0.0"（解析到 2.3.4，其 peer = vite ^2.5.10 ⇒ 与 2.9.18 匹配）。

用法：
    python verify_d2c1b_vite_pin.py              # 全量
    python verify_d2c1b_vite_pin.py --selftest   # 量尺前置断言（P-5）
    python verify_d2c1b_vite_pin.py --static-only

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
import json
import os
import re
import subprocess
import sys

ROOT = USDT_ROOT
WEB = os.path.join(ROOT, "03-web-admin")
PKG = os.path.join(WEB, "package.json")
LOCK = os.path.join(WEB, "package-lock.json")
VITE = os.path.join(WEB, "vite.config.js")
STATIC_DASH = os.path.join(WEB, "static", "admin_dashboard.html")
STATIC_LOGIN = os.path.join(WEB, "static", "admin_login.html")
DIST = os.path.join(WEB, "dist")
MANIFEST = os.path.join(ROOT, "_manifest.sha256")

NPM = r"E:\CTF\runtime\node\npm.cmd"
NODE_DIR = r"E:\CTF\runtime\node"

BASE = {
    PKG: "5face9ec603725492ba8b96e14ac9b9111b35b22729ae032ae43602d18151e67",
    VITE: "e084dc2dd8608bf82779756eb8cbec50924f9f5177a97e5b09979e14161a2ea1",
    STATIC_DASH: "9bad2f7f3a047a9fb988ca9f0c022df2db61b05ac2d548c74449eecdd6b85ce5",
    STATIC_LOGIN: "2674aeab104190b8725a2d33fbdac010295a2891cd317726c2e40b6fece8a8c5",
    MANIFEST: "b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2",
}

# ★ 除 plugin-vue 外，其他依赖行的期望值（防改过头）—— 取自 base 版本
EXPECT_OTHER_DEPS = {
    "axios": "^0.19.2",
    "vite": "^2.8.0",
    "vue": "^3.2.25",
    "@vue/cli-plugin-vuex": "~4.5.0",
    "eslint-plugin-vue": "^7.0.0",
}

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


def run_npm(args, timeout=1800):
    env = dict(os.environ)
    env["PATH"] = NODE_DIR + os.pathsep + env.get("PATH", "")
    try:
        r = subprocess.run([NPM] + args, cwd=WEB, env=env, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return r.returncode, (r.stdout or ""), (r.stderr or "")
    except subprocess.TimeoutExpired:
        return -999, "", f"TIMEOUT after {timeout}s"
    except Exception as e:
        return -998, "", f"EXC:{e}"


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    for p in (PKG, VITE, STATIC_DASH, STATIC_LOGIN):
        exists = os.path.isfile(p)
        print(f"  {'存在' if exists else '[FAIL] 缺失'}: {os.path.relpath(p, ROOT)}")
        if not exists:
            ok = False

    # ★ 量尺有效性：必须能解析出 package.json 的依赖
    try:
        j = json.loads(open(PKG, encoding="utf-8").read())
        deps = list((j.get("devDependencies") or {}).keys()) + \
               list((j.get("dependencies") or {}).keys())
        pv = (j.get("devDependencies") or {}).get("@vitejs/plugin-vue") or \
             (j.get("dependencies") or {}).get("@vitejs/plugin-vue")
        print(f"  量尺有效：解析出 {len(deps)} 个依赖；plugin-vue = {pv!r}")
        if pv is None:
            print("  [FAIL] 未解析到 @vitejs/plugin-vue ⇒ 量尺坏了")
            ok = False
    except Exception as e:
        print(f"  [FAIL] package.json 解析失败: {e}")
        ok = False

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--static-only", action="store_true")
    ap.add_argument("--skip-npm", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== D2-C1b 钉住 plugin-vue 版本判据 ===")
    print("")

    # ---- X1: plugin-vue 已钉住 ----
    print("X1 plugin-vue 不再是 \"latest\":")
    try:
        j = json.loads(open(PKG, encoding="utf-8").read())
    except Exception as e:
        rec("X1 package.json 可解析", False, str(e))
        j = {}
    dd = j.get("devDependencies") or {}
    deps = j.get("dependencies") or {}
    pv = dd.get("@vitejs/plugin-vue", deps.get("@vitejs/plugin-vue"))
    rec("X1 plugin-vue 版本非 latest", pv is not None and pv != "latest",
        f"当前 = {pv!r}" + ("  ★ 仍是 latest" if pv == "latest" else ""))

    # ---- X2: 其他依赖未变 ----
    print("")
    print("X2 ★ 防改过头：其他依赖行未变:")
    changed = []
    for k, want in EXPECT_OTHER_DEPS.items():
        got = dd.get(k, deps.get(k))
        if got != want:
            changed.append(f"{k}: {want!r} -> {got!r}")
    rec("X2 其他依赖未被改", len(changed) == 0,
        f"★ 被改: {changed}" if changed else f"{len(EXPECT_OTHER_DEPS)} 个依赖均未变")

    # ---- X6/X7/X8: 守护 ----
    print("")
    print("X6/X7/X8 ★ 守护:")
    for p, want, label in (
        (VITE, BASE[VITE], "vite.config.js"),
        (STATIC_DASH, BASE[STATIC_DASH], "static/admin_dashboard.html"),
        (STATIC_LOGIN, BASE[STATIC_LOGIN], "static/admin_login.html"),
        (MANIFEST, BASE[MANIFEST], "_manifest.sha256"),
    ):
        if os.path.isfile(p):
            cur = sha256(p)
            rec(f"X8 {label} 未改", cur == want, f"{cur[:16]}…")
    # src/ 只做文件数核对（内容太多）
    src = os.path.join(WEB, "src")
    if os.path.isdir(src):
        n = sum(len(f) for _, _, f in os.walk(src))
        rec("X7 src/ 文件数未变（149）", n == 149, f"{n} 个文件")

    # ---- 记录 plugin-vue 实际装了什么（信息性）----
    print("")
    pv_pkg = os.path.join(WEB, "node_modules", "@vitejs", "plugin-vue", "package.json")
    if os.path.isfile(pv_pkg):
        try:
            pj = json.loads(open(pv_pkg, encoding="utf-8").read())
            print(f"  已装 @vitejs/plugin-vue = {pj.get('version')}")
            print(f"    其 peer vite = {(pj.get('peerDependencies') or {}).get('vite')}")
        except Exception:
            pass
    vite_pkg = os.path.join(WEB, "node_modules", "vite", "package.json")
    if os.path.isfile(vite_pkg):
        try:
            vj = json.loads(open(vite_pkg, encoding="utf-8").read())
            print(f"  已装 vite = {vj.get('version')}")
        except Exception:
            pass

    # ---- X3/X4/X5: npm ci + build ----
    if args.static_only or args.skip_npm:
        print("")
        print("[SKIP] X3/X4/X5 被跳过 —— SKIP 不等于 PASS（P-13）")
    else:
        print("")
        print("X3 ★ npm ci:")
        rc, out, err = run_npm(["ci"], timeout=1800)
        tail = (out + err).strip().splitlines()[-8:]
        for l in tail:
            print(f"    {l[:120]}")
        rec("X3 npm ci EXIT=0", rc == 0, f"EXIT={rc}")

        print("")
        print("X4 ★ npm run build:")
        rc2, out2, err2 = run_npm(["run", "build"], timeout=1800)
        tail2 = (out2 + err2).strip().splitlines()[-12:]
        for l in tail2:
            print(f"    {l[:130]}")
        rec("X4 npm run build EXIT=0", rc2 == 0, f"EXIT={rc2}")

        # X5: dist/
        if os.path.isdir(DIST):
            n = sum(len(f) for _, _, f in os.walk(DIST))
            sz = sum(os.path.getsize(os.path.join(dp, f))
                     for dp, _, fns in os.walk(DIST) for f in fns)
            rec("X5 产出 dist/", n > 0, f"{n} 个文件 / {sz/1024/1024:.2f} MB")
        else:
            rec("X5 产出 dist/", False, "★ dist/ 不存在")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  版本已钉住、其他依赖未变、npm ci 与 build 均通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
