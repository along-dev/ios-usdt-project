# -*- coding: utf-8 -*-
"""
D1-C2 判据：track 三条路径的【复用验证】（本卡结论：无需新建代码）。

★★ 依据（调度已实测）：
   Owner 裁 (a) 复用 ⇒ 不新建 `plugins/android/track.js`。
   `04-landing/templates/vodex.html:485-492`（Android 侧模板）已按既有字段调用：
     postJSON('/api/track/start',     {sid, lang, url})
     postJSON('/api/track/heartbeat', {sid, dwell})
     postJSON('/api/track/click',     {sid, dwell})
   既有 `landing.js` 的字段与之 1:1 对应 ⇒ 复用的实质 = 保持现状 + 验证可用。

★ 本卡是【纯验证卡】—— 不修改任何产物。
★ T4/T5 是"防重复注册"核心：若 D1 阶段有人新增 track 路由，Fastify 会启动失败。

用法：
    python verify_d1c2_track_reuse.py              # 全量
    python verify_d1c2_track_reuse.py --selftest   # 量尺前置断言（P-5）

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
import sys
import urllib.error
import urllib.request

ROOT = USDT_ROOT
BE = os.path.join(ROOT, "02-backend-node", "src_restored")
LANDING_JS = os.path.join(BE, "plugins", "api", "routes", "landing.js")
VODEX = os.path.join(ROOT, "04-landing", "templates", "vodex.html")
MANIFEST = os.path.join(ROOT, "_manifest.sha256")

BASE = {
    LANDING_JS: "3208c207bf423c8d99577c0508e9b6cc809f471dcd590ee0e96b87906e7de632",
    VODEX: "6f2e2a1969703d2e9a3e008774b0fd16271172e12695d2911b6072de5e05bc4d",
    MANIFEST: "b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2",
}

API = "http://127.0.0.1:3000"
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


def http(method, path, body=None, timeout=12):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return -1, f"EXC:{e}".encode()


def all_track_registrations():
    """扫描 src_restored 下所有 /api/track/* 的注册点（防重复注册）。"""
    out = []
    for dp, _dn, fns in os.walk(BE):
        if "node_modules" in dp:
            continue
        for fn in fns:
            if not fn.endswith(".js"):
                continue
            p = os.path.join(dp, fn)
            s = read(p)
            for m in re.finditer(
                    r"fastify\.(get|post|put|delete)\(\s*['\"`](/api/track/[a-z]+)['\"`]", s):
                line = s[:m.start()].count("\n") + 1
                out.append((os.path.relpath(p, BE), line, m.group(1).upper(), m.group(2)))
    return out


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    for p in (LANDING_JS, VODEX):
        print(f"  {'存在' if os.path.isfile(p) else '[FAIL] 缺失'}: {os.path.relpath(p, ROOT)}")
        if not os.path.isfile(p):
            ok = False

    # 量尺有效性：正则须能命中 track 注册
    sample = "fastify.post('/api/track/start', async (request, reply) => {"
    if re.search(r"fastify\.post\(\s*['\"`](/api/track/[a-z]+)", sample):
        print("  模式有效：可命中 /api/track/* 注册")
    else:
        print("  [FAIL] 模式失效")
        ok = False

    # 预检：当前注册点
    regs = all_track_registrations()
    print(f"  当前 /api/track/* 注册点：{len(regs)} 处")
    for f, ln, m, path in regs:
        print(f"    {f}:{ln}  {m} {path}")

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--skip-http", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== D1-C2 track 复用验证（纯验证卡）===")
    print("")

    # ---- T6: TOUCH_THROTTLE_MS ----
    print("T6 限频参数未被动过:")
    ls = read(LANDING_JS)
    m = re.search(r"TOUCH_THROTTLE_MS\s*=\s*(\d+)", ls)
    val = int(m.group(1)) if m else -1
    rec("T6 TOUCH_THROTTLE_MS == 3000", val == 3000, f"实际 = {val}")

    # ---- T4: 注册点唯一 ----
    print("")
    print("T4 ★ 防重复注册（每条路径应【只有一处】注册）:")
    regs = all_track_registrations()
    by_path = {}
    for f, ln, meth, path in regs:
        by_path.setdefault(path, []).append((f, ln, meth))
    for path in ("/api/track/start", "/api/track/heartbeat", "/api/track/click"):
        occ = by_path.get(path, [])
        rec(f"T4 {path} 仅 1 处注册", len(occ) == 1,
            f"{len(occ)} 处: {occ}" if len(occ) != 1 else f"{occ[0][0]}:{occ[0][1]}")
    # 额外：不得存在 plugins/android/track.js
    track_js = os.path.join(BE, "plugins", "android", "track.js")
    rec("T4 未新建 plugins/android/track.js（Owner 裁复用）",
        not os.path.isfile(track_js),
        "不存在 ✓" if not os.path.isfile(track_js) else "★ 被新建（与裁决矛盾）")

    # ---- T7: 守护 ----
    print("")
    print("T7 ★ 守护：不得改的文件的:")
    rec("T7 landing.js 未改", sha256(LANDING_JS) == BASE[LANDING_JS],
        f"{sha256(LANDING_JS)[:16]}…")
    rec("T7 vodex.html 未改", sha256(VODEX) == BASE[VODEX], f"{sha256(VODEX)[:16]}…")
    rec("T7 _manifest.sha256 未改", sha256(MANIFEST) == BASE[MANIFEST],
        f"{sha256(MANIFEST)[:16]}…")

    # ---- T1–T3: 真 HTTP（按 vodex.html 的确切 body）----
    print("")
    print("T1–T3 真 HTTP（按 vodex.html 的确切字段）:")
    if args.skip_http:
        print("  [SKIP] 被 --skip-http 跳过 —— SKIP 不等于 PASS（P-13）")
    else:
        # ★★ 修正（2026-09-30，自查）：
        #   初版传 `sid: ""` ⇒ 被 normalizeSid 拒绝（400 "sid 非法"）——
        #   **那是正确的既有行为**，不是缺陷；是我的用例构造错了。
        #   ★ 实测 `vodex.html:477-480` 的 `genSid()`：
        #       crypto.randomUUID().replace(/-/g,'')      ⇒ **32 位 hex**
        #     故用例须用同格式的 sid。
        import uuid
        sid_seed = uuid.uuid4().hex           # 32 位 hex，与 genSid 同格式
        print(f"    （构造 sid = {sid_seed}，格式同 vodex.html:478 的 genSid）")

        # T1: start（body 照 vodex.html:485）
        st1, b1 = http("POST", "/api/track/start",
                       {"sid": sid_seed, "lang": "zh-CN",
                        "url": "http://127.0.0.1:3000/vodex.html"})
        j1 = None
        try:
            j1 = json.loads(b1.decode("utf-8", "replace"))
        except Exception:
            pass
        sid = (j1 or {}).get("data", {}).get("sid") if isinstance(j1, dict) else None
        rec("T1 POST /api/track/start（vodex 字段 + 合法 sid）=> 200 且返回 sid",
            st1 == 200 and bool(sid),
            f"HTTP={st1} body={b1.decode('utf-8','replace')[:150]}")

        # T1b: 非法 sid 必须被拒（既有行为，防改过头）
        st1b, b1b = http("POST", "/api/track/start", {"sid": "!!!", "lang": "", "url": ""})
        rec("T1b 非法 sid => 400（既有校验未失效）", st1b == 400,
            f"HTTP={st1b} body={b1b.decode('utf-8','replace')[:100]}")

        if sid:
            # T2: heartbeat 用 start 返回的 sid（vodex.html:486 的语义）
            st2, b2 = http("POST", "/api/track/heartbeat", {"sid": sid, "dwell": 15000})
            j2 = None
            try:
                j2 = json.loads(b2.decode("utf-8", "replace"))
            except Exception:
                pass
            ok2 = st2 == 200 and isinstance(j2, dict) and j2.get("code") == 0
            rec("T2 POST /api/track/heartbeat（sid 往返 + dwell）",
                ok2, f"HTTP={st2} body={b2.decode('utf-8','replace')[:150]}")

            # T3: click（vodex.html:492 的语义）
            st3, b3 = http("POST", "/api/track/click", {"sid": sid, "dwell": 16000})
            j3 = None
            try:
                j3 = json.loads(b3.decode("utf-8", "replace"))
            except Exception:
                pass
            ok3 = st3 == 200 and isinstance(j3, dict) and j3.get("code") == 0
            rec("T3 POST /api/track/click（sid 往返 + dwell）",
                ok3, f"HTTP={st3} body={b3.decode('utf-8','replace')[:150]}")
        else:
            print("  [SKIP] 无 sid ⇒ T2/T3 无法执行")

        # T5: Fastify 未因重复路由启动失败（服务存活 + 三条可达）
        st5a, _ = http("POST", "/api/track/start", {"sid": "", "lang": "", "url": ""})
        rec("T5 服务存活且 track 端点可达（未因重复路由崩溃）",
            st5a in (200, 400), f"HTTP={st5a}")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  三条 track 复用可用、注册唯一、限频未动")
    return 0


if __name__ == "__main__":
    sys.exit(main())
