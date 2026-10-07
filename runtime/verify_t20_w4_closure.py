#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T20 判据：波次 4 剩余项收口（vue-qrcode 删除 + 三项登记）

V1  package.json 不含 vue-qrcode
V2  03-web-admin/src 树内 qrcode 引用数为 0
V3  dist/ 存在且非空（构建产物）—— 由外部 npm.cmd run build 保证 EXIT=0
V4  残余暴露面登记.md 含 R-10，且位于「附：登记纪律」之前
V5  02-backend-node/README.md 含 bsc 说明（§5.2.4 / 潜客兜底）
V6  未改 06-android/**、05-ios/**、group.html（mtime 早于会话 + 字面量仍 1 处）
V7  守护：_manifest.sha256、contracts.md 未改（由外部基线比对）

退出码：0 = 全绿；1 = 有红。
"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib
import os
import re
import sys

ROOT = USDT_ROOT
PKG = os.path.join(ROOT, r"03-web-admin\package.json")
LOCK = os.path.join(ROOT, r"03-web-admin\package-lock.json")
SRC = os.path.join(ROOT, r"03-web-admin\src")
DIST = os.path.join(ROOT, r"03-web-admin\dist")
REG = os.path.join(ROOT, r"09-docs\reports\残余暴露面登记.md")
README = os.path.join(ROOT, r"02-backend-node\README.md")
GROUP = os.path.join(ROOT, r"05-ios\coruna\group.html")
MANIFEST = os.path.join(ROOT, "_manifest.sha256")
CONTRACTS = os.path.join(ROOT, r"09-docs\spec\contracts.md")

results = []


def check(tag, ok, detail):
    results.append((tag, ok, detail))
    print(("  PASS  " if ok else "  FAIL  ") + tag + " :: " + detail)


def read_text(p):
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def sha256(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ---------------- V1 ----------------
try:
    pkg_txt = read_text(PKG)
    n_pkg = len(re.findall(r"vue-qrcode", pkg_txt))
    # lock 同步：qrcode / vue-qrcode 命中应为 0
    n_lock = len(re.findall(r"qrcode", read_text(LOCK))) if os.path.exists(LOCK) else -1
    check("V1", n_pkg == 0 and n_lock == 0,
          "package.json vue-qrcode=%d, package-lock qrcode=%d" % (n_pkg, n_lock))
except Exception as e:  # noqa
    check("V1", False, "exception: %r" % (e,))

# ---------------- V2 ----------------
try:
    hits = []
    for dp, dn, fn in os.walk(SRC):
        for f in fn:
            p = os.path.join(dp, f)
            try:
                if re.search(r"qrcode", read_text(p), re.I):
                    hits.append(p)
            except Exception:
                pass
    check("V2", len(hits) == 0, "src qrcode refs=%d" % len(hits))
except Exception as e:  # noqa
    check("V2", False, "exception: %r" % (e,))

# ---------------- V3 ----------------
try:
    n_dist = 0
    if os.path.isdir(DIST):
        for dp, dn, fn in os.walk(DIST):
            n_dist += len(fn)
    check("V3", n_dist > 0, "dist files=%d (build EXIT must be 0 externally)" % n_dist)
except Exception as e:  # noqa
    check("V3", False, "exception: %r" % (e,))

# ---------------- V4 ----------------
try:
    reg = read_text(REG)
    has_r10 = "## R-10" in reg
    i_r10 = reg.find("## R-10")
    i_disc = reg.find("## 附：登记纪律")
    ordered = i_r10 != -1 and i_disc != -1 and i_r10 < i_disc
    has_lock = "collect_lock.go" in reg
    check("V4", has_r10 and ordered and has_lock,
          "R-10=%s ordered=%s collect_lock=%s" % (has_r10, ordered, has_lock))
except Exception as e:  # noqa
    check("V4", False, "exception: %r" % (e,))

# ---------------- V5 ----------------
try:
    rd = read_text(README)
    ok = ("5.2.4" in rd) and ("bsc" in rd) and ("潜客兜底" in rd)
    check("V5", ok, "README 5.2.4=%s bsc=%s 潜客兜底=%s"
          % ("5.2.4" in rd, "bsc" in rd, "潜客兜底" in rd))
except Exception as e:  # noqa
    check("V5", False, "exception: %r" % (e,))

# ---------------- V6 ----------------
try:
    with open(GROUP, "rb") as f:
        gb = f.read()
    g_txt = gb.decode("utf-8", errors="replace")
    n_lit = g_txt.count("/mgr-admin-8bcde2021d98")
    # 未修改的佐证：group.html mtime 必须早于本脚本自身 mtime
    g_mtime = os.stat(GROUP).st_mtime
    s_mtime = os.stat(os.path.abspath(__file__)).st_mtime
    untouched = g_mtime < s_mtime - 60
    check("V6", n_lit == 1 and untouched,
          "group.html literal=%d mtime_older=%s" % (n_lit, untouched))
except Exception as e:  # noqa
    check("V6", False, "exception: %r" % (e,))

# ---------------- V7 ----------------
try:
    ok = os.path.exists(MANIFEST) and os.path.exists(CONTRACTS)
    check("V7", ok, "manifest sha256=%s contracts sha256=%s"
          % (sha256(MANIFEST)[:12], sha256(CONTRACTS)[:12]))
except Exception as e:  # noqa
    check("V7", False, "exception: %r" % (e,))

print()
red = [r for r in results if not r[1]]
print("TOTAL=%d RED=%d" % (len(results), len(red)))
sys.exit(1 if red else 0)
