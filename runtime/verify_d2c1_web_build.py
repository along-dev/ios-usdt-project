# -*- coding: utf-8 -*-
"""
D2-C1 判据：03-web-admin 可构建（补 lock + npm ci + build）。

★ 现状（调度实测）：
   package-lock.json 不存在、node_modules 不存在、registry 可访问。
   static/ 已有产物（admin_dashboard.html / admin_login.html）⇒ **运行时不依赖本卡**。

★★ 关键：vite.config.js:74 的 `outDir: 'dist'` ⇒ 构建产物在 dist/，
   **不会覆盖 static/**（本卡不得改 static/）。

用法：
    python verify_d2c1_web_build.py              # 全量
    python verify_d2c1_web_build.py --selftest   # 量尺前置断言（P-5）
    python verify_d2c1_web_build.py --static-only  # 只做静态断言（不跑 npm，快）

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
import subprocess
import sys

ROOT = USDT_ROOT
WEB = os.path.join(ROOT, "03-web-admin")
PKG = os.path.join(WEB, "package.json")
LOCK = os.path.join(WEB, "package-lock.json")
NM = os.path.join(WEB, "node_modules")
VITE = os.path.join(WEB, "vite.config.js")
STATIC_DASH = os.path.join(WEB, "static", "admin_dashboard.html")
STATIC_LOGIN = os.path.join(WEB, "static", "admin_login.html")
MANIFEST = os.path.join(ROOT, "_manifest.sha256")

NPM = r"E:\CTF\runtime\node\npm.cmd"
NODE_DIR = r"E:\CTF\runtime\node"

BASE = {
    # ★ 更新（2026-09-30）：D2-C1b 已由 Owner 授权把 plugin-vue 从 "latest" 钉为 "^2.0.0"
    #   ⇒ package.json 的期望哈希随之更新（**受控变更**，非漂移）。
    PKG: "872b1f7dc73969aeabe3d3360642c2ed88c23de7991d6928101ce6a85f2ca593",
    VITE: "e084dc2dd8608bf82779756eb8cbec50924f9f5177a97e5b09979e14161a2ea1",
    STATIC_DASH: "9bad2f7f3a047a9fb988ca9f0c022df2db61b05ac2d548c74449eecdd6b85ce5",
    STATIC_LOGIN: "2674aeab104190b8725a2d33fbdac010295a2891cd317726c2e40b6fece8a8c5",
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


def run_npm(args, timeout=1200):
    """在 03-web-admin 内跑 npm（★ node 不在 PATH，需前置）。"""
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
        print(f"  {'存在' if os.path.isfile(p) else '[FAIL] 缺失'}: {os.path.relpath(p, ROOT)}")
        if not os.path.isfile(p):
            ok = False

    # ★ 量尺有效性：vite outDir 必须是 dist（证明不会覆盖 static）
    if os.path.isfile(VITE):
        s = open(VITE, encoding="utf-8", errors="replace").read()
        import re
        m = re.search(r"outDir\s*:\s*['\"]([^'\"]+)['\"]", s)
        outdir = m.group(1) if m else None
        if outdir:
            print(f"  vite outDir = {outdir}")
            if outdir.replace("\\", "/").strip("./") not in ("dist",):
                print(f"  [WARN] outDir 不是 dist —— 可能覆盖 static（须人工确认）")
        else:
            print("  [WARN] 未找到 outDir")

    print(f"  npm.cmd 存在: {os.path.isfile(NPM)}")
    print(f"  package-lock.json 存在: {os.path.isfile(LOCK)}")
    print(f"  node_modules 存在: {os.path.isdir(NM)}")

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--static-only", action="store_true", help="只做静态断言，不跑 npm")
    ap.add_argument("--skip-install", action="store_true", help="跳过 npm install")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== D2-C1 03-web-admin 可构建判据 ===")
    print("")

    # ---- W3/W4/W5/W6: 守护（先做，避免被构建过程意外改到）----
    print("W3/W4/W5/W6 ★ 守护:")
    rec("W5 package.json 未改", sha256(PKG) == BASE[PKG], f"{sha256(PKG)[:16]}…")
    rec("W5 vite.config.js 未改", sha256(VITE) == BASE[VITE], f"{sha256(VITE)[:16]}…")
    rec("W4 static/admin_dashboard.html 未改", sha256(STATIC_DASH) == BASE[STATIC_DASH],
        f"{sha256(STATIC_DASH)[:16]}…")
    rec("W4 static/admin_login.html 未改", sha256(STATIC_LOGIN) == BASE[STATIC_LOGIN],
        f"{sha256(STATIC_LOGIN)[:16]}…")
    if os.path.isfile(MANIFEST):
        rec("W6 _manifest.sha256 未改",
            sha256(MANIFEST) == "b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2",
            f"{sha256(MANIFEST)[:16]}…")

    if args.static_only:
        print("")
        print("[SKIP] W1/W2 被 --static-only 跳过 —— SKIP 不等于 PASS（P-13）")
    else:
        # ---- W1: package-lock.json + npm ci ----
        print("")
        print("W1 ★ lock 文件 + npm ci:")
        if not os.path.isfile(LOCK):
            if args.skip_install:
                rec("W1 package-lock.json 存在", False, "★ 不存在（且 --skip-install 跳过生成）")
            else:
                print("    package-lock.json 不存在 ⇒ 先跑 npm install 生成…")
                rc, out, err = run_npm(["install"], timeout=1800)
                print(f"    npm install EXIT={rc}")
                tail = (out + err).strip().splitlines()[-8:]
                for l in tail:
                    print(f"      {l[:120]}")
                rec("W1 npm install 成功", rc == 0, f"EXIT={rc}")
        else:
            print(f"    package-lock.json 已存在（{os.path.getsize(LOCK)} B）")

        if os.path.isfile(LOCK):
            print("    跑 npm ci…")
            rc, out, err = run_npm(["ci"], timeout=1800)
            print(f"    npm ci EXIT={rc}")
            tail = (out + err).strip().splitlines()[-8:]
            for l in tail:
                print(f"      {l[:120]}")
            rec("W1 npm ci 成功", rc == 0, f"EXIT={rc}")
        else:
            rec("W1 lock 可用", False, "★ lock 文件缺失，无法 npm ci")

        # ---- W2: npm run build ----
        print("")
        print("W2 ★ npm run build:")
        rc, out, err = run_npm(["run", "build"], timeout=1800)
        print(f"    npm run build EXIT={rc}")
        tail = (out + err).strip().splitlines()[-12:]
        for l in tail:
            print(f"      {l[:130]}")
        rec("W2 npm run build 成功", rc == 0, f"EXIT={rc}")

        # 构建产物
        dist = os.path.join(WEB, "dist")
        if os.path.isdir(dist):
            n = sum(len(f) for _, _, f in os.walk(dist))
            rec("W2 产出 dist/（vite outDir）", n > 0, f"{n} 个文件")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  03-web-admin 可 npm ci 且可 build，且 src/static 未被改")
    return 0


if __name__ == "__main__":
    sys.exit(main())
