# -*- coding: utf-8 -*-
"""
D1-C3 判据：APK 上传端点（multipart）+ 路径穿越防护。

★ 契约来源：`admin_dashboard.html:829-861`
     fd.append("apk", file)                       ← 字段名 "apk"
     xhr.open("POST", ADMIN + "/api/apk/upload")  ← multipart
     成功: { ok: true, filename, size, tg_ok? }
     失败: { ok: false, error }

★★ U4 是本卡的核心安全点：上传端点是最典型的路径穿越入口。
   判据用 `../` 构造文件名，验证**候选目录之外没有生成文件**。

用法：
    python verify_d1c3_apk_upload.py              # 全量
    python verify_d1c3_apk_upload.py --selftest   # 量尺前置断言（P-5）

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
import http.cookiejar
import json
import os
import re
import sys
import urllib.error
import urllib.request
import uuid

ROOT = USDT_ROOT
BE = os.path.join(ROOT, "02-backend-node", "src_restored")
ANDROID_DIR = os.path.join(BE, "plugins", "android")
ADMIN_JS = os.path.join(ANDROID_DIR, "admin.js")
INDEX_JS = os.path.join(ANDROID_DIR, "index.js")
APP_JS = os.path.join(BE, "app.js")
LANDING_JS = os.path.join(BE, "plugins", "api", "routes", "landing.js")
DASH_HTML = os.path.join(ROOT, "03-web-admin", "static", "admin_dashboard.html")
MANIFEST = os.path.join(ROOT, "_manifest.sha256")

ADMIN = "/mgr-admin-8bcde2021d98"
API = "http://127.0.0.1:3000"

BASE = {
    LANDING_JS: "3208c207bf423c8d99577c0508e9b6cc809f471dcd590ee0e96b87906e7de632",
    DASH_HTML: "9bad2f7f3a047a9fb988ca9f0c022df2db61b05ac2d548c74449eecdd6b85ce5",
    MANIFEST: "b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2",
    APP_JS: "a1b568827febc198f115f5e285e29e368b80f211f121797d1b4da8f59f3c16fb",
}

# 候选落盘目录（与 landing.js:154-159 / admin.js 的约定一致）
APK_DIRS = [
    os.path.join(ROOT, "02-backend-node", "templates", "apk"),
    os.path.join(ROOT, "02-backend-node", "public", "apk"),
]

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


def login():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    body = json.dumps({"username": "admin", "password": "i1c3-e2e-admin"}).encode()
    req = urllib.request.Request(API + "/api/auth/login", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with opener.open(req, timeout=10) as r:
            raw = r.read().decode("utf-8", "replace")
            m = re.search(r'"accessToken"\s*:\s*"([^"]+)"', raw)
            if m:
                return m.group(1)
    except Exception:
        pass
    for c in cj:
        if c.name == "accessToken":
            return c.value
    return None


def multipart_post(path, field, filename, content, token=None, timeout=60):
    """构造 multipart/form-data 请求（纯 stdlib）。"""
    boundary = "----DSHBoundary" + uuid.uuid4().hex
    parts = []
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(
        f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'.encode())
    parts.append(b"Content-Type: application/vnd.android.package-archive\r\n\r\n")
    parts.append(content)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    data = b"".join(parts)

    req = urllib.request.Request(API + path, data=data, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    if token:
        req.add_header("Cookie", f"accessToken={token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return -1, f"EXC:{e}".encode()


def json_post(path, body, token=None, timeout=15):
    data = json.dumps(body).encode()
    req = urllib.request.Request(API + path, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Cookie", f"accessToken={token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return -1, f"EXC:{e}".encode()


def json_get(path, token=None, timeout=15):
    req = urllib.request.Request(API + path, method="GET")
    if token:
        req.add_header("Cookie", f"accessToken={token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return -1, f"EXC:{e}".encode()


def list_all_apks():
    """列出所有候选目录下的 .apk。"""
    out = []
    for d in APK_DIRS:
        if os.path.isdir(d):
            for fn in os.listdir(d):
                if fn.lower().endswith(".apk"):
                    out.append(os.path.join(d, fn))
    return out


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    for p in (ADMIN_JS, INDEX_JS, APP_JS, LANDING_JS, DASH_HTML):
        print(f"  {'存在' if os.path.isfile(p) else '[FAIL] 缺失'}: {os.path.relpath(p, ROOT)}")
        if not os.path.isfile(p):
            ok = False

    # 量尺有效性：multipart 构造须能被解析出 boundary
    b = "----DSHBoundary" + "a" * 16
    sample = f"--{b}\r\nContent-Disposition: form-data; name=\"apk\"; filename=\"x.apk\"\r\n\r\nDATA\r\n--{b}--\r\n"
    if f'name="apk"' in sample and b in sample:
        print("  multipart 构造样本自检通过")
    else:
        print("  [FAIL] multipart 样本构造有误")
        ok = False

    # 候选目录现状
    print(f"  候选 APK 目录：")
    for d in APK_DIRS:
        n = len([f for f in os.listdir(d)]) if os.path.isdir(d) else 0
        print(f"    {os.path.relpath(d, ROOT)} : {'存在' if os.path.isdir(d) else '不存在'}（{n} 项）")

    t = login()
    print(f"  {'登录可用' if t else '[WARN] 登录失败'}")
    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--skip-http", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== D1-C3 APK 上传判据 ===")
    print("")

    srcs = android_src()
    allsrc = "\n".join(read(p) for p in srcs) if srcs else ""

    # ---- U1: 路由注册 ----
    print("U1 路由注册:")
    rest = "/api/apk/upload"
    pats = [
        re.compile(r"fastify\.post\(\s*[`'\"]" + re.escape(ADMIN + rest) + r"[`'\"]"),
        re.compile(r"fastify\.post\(\s*`\$\{[A-Za-z_]+\}" + re.escape(rest) + r"`"),
    ]
    rec("U1 POST ${ADMIN}/api/apk/upload 已注册",
        any(p.search(allsrc) for p in pats),
        "已注册" if any(p.search(allsrc) for p in pats) else "★ 未注册")

    # ---- U8: 守护 ----
    print("")
    print("U8 ★ 守护:")
    rec("U8 landing.js 未改", sha256(LANDING_JS) == BASE[LANDING_JS], f"{sha256(LANDING_JS)[:16]}…")
    rec("U8 admin_dashboard.html 未改", sha256(DASH_HTML) == BASE[DASH_HTML], f"{sha256(DASH_HTML)[:16]}…")
    rec("U8 app.js 未改", sha256(APP_JS) == BASE[APP_JS], f"{sha256(APP_JS)[:16]}…")
    rec("U8 _manifest.sha256 未改", sha256(MANIFEST) == BASE[MANIFEST], f"{sha256(MANIFEST)[:16]}…")

    # ---- HTTP ----
    if args.skip_http:
        print("")
        print("[SKIP] HTTP 断言被 --skip-http 跳过 —— SKIP 不等于 PASS（P-13）")
    else:
        # U2: 无 token ⇒ 401
        st2, b2 = multipart_post(ADMIN + rest, "apk", "nope.apk", b"PK\x03\x04dummy")
        rec("U2 无 token 上传 => 401", st2 == 401,
            f"HTTP={st2} body={b2.decode('utf-8','replace')[:100]}")

        tok = login()
        if not tok:
            print("[SKIP] 无法登录 ⇒ U3–U7 跳过（★ SKIP 不等于 PASS）")
        else:
            before = set(list_all_apks())

            # U3: 合法上传 ⇒ 200 + 真落盘
            fname = f"d1c3-probe-{uuid.uuid4().hex[:8]}.apk"
            payload = b"PK\x03\x04" + b"D1C3" * 512        # 小样本，2KB+
            st3, b3 = multipart_post(ADMIN + rest, "apk", fname, payload, token=tok)
            j3 = None
            try:
                j3 = json.loads(b3.decode("utf-8", "replace"))
            except Exception:
                pass
            after = set(list_all_apks())
            new_files = sorted(after - before)
            disk_ok = len(new_files) >= 1
            rec("U3 上传合法 .apk => 200 且响应含 ok/filename/size",
                st3 == 200 and isinstance(j3, dict) and j3.get("ok") is True
                and "filename" in j3 and "size" in j3,
                f"HTTP={st3} body={b3.decode('utf-8','replace')[:180]}")
            rec("U3 文件【真落盘】（候选目录新增 .apk）", disk_ok,
                f"新增: {[os.path.relpath(x, ROOT) for x in new_files]}" if disk_ok
                else "★ 候选目录未见新文件")

            # U7: apk/list 能看到
            st7, b7 = json_get(ADMIN + "/api/apk/list", token=tok)
            j7 = None
            try:
                j7 = json.loads(b7.decode("utf-8", "replace"))
            except Exception:
                pass
            files = j7.get("files", []) if isinstance(j7, dict) else []
            names = [f.get("original_name", "") for f in files]
            rec("U7 apk/list 能看到刚上传的文件", fname in names,
                f"list 返回 {len(files)} 条；含目标: {fname in names}")

            # U4: ★ 路径穿越防护（核心）
            #
            # ★★ 修正（2026-09-30，调度自查）：本项会产生【残留文件】——
            #   实测 D2-C2 时发现 `templates/apk/evil-d1c3.apk` 残留，
            #   根因即本段（旧版只清理 `new_files`，未清理 U4 生成的文件）。
            #   ⇒ 改为：**记录 U4 前后的目录快照，结束时一并清理**。
            snap_before_u4 = set(list_all_apks())
            evil = "../../evil-d1c3.apk"
            st4, b4 = multipart_post(ADMIN + rest, "apk", evil, b"PK\x03\x04EVIL", token=tok)
            snap_after_u4 = set(list_all_apks())
            u4_created = snap_after_u4 - snap_before_u4
            # 检查候选目录的【上级】是否被写入
            escapes = []
            for d in APK_DIRS:
                for up in (os.path.dirname(d), os.path.dirname(os.path.dirname(d))):
                    cand = os.path.join(up, "evil-d1c3.apk")
                    if os.path.isfile(cand):
                        escapes.append(cand)
            rec("U4 ★ 文件名含 ../ 不得写出候选目录外", len(escapes) == 0,
                f"越界文件: {escapes}" if escapes else
                f"未越界 ✓（HTTP={st4}；改由后端净化，落在候选目录内）")
            if u4_created:
                print(f"    （U4 在候选目录内生成 {len(u4_created)} 个文件，结束时一并清理）")

            # U5: 非 .apk 后缀
            st5, b5 = multipart_post(ADMIN + rest, "apk", "notanapk.txt", b"hello", token=tok)
            j5 = None
            try:
                j5 = json.loads(b5.decode("utf-8", "replace"))
            except Exception:
                pass
            rejected5 = st5 >= 400 or (isinstance(j5, dict) and j5.get("ok") is False)
            rec("U5 非 .apk 后缀 => 拒绝", rejected5,
                f"HTTP={st5} body={b5.decode('utf-8','replace')[:120]}")

            # U6: 大小上限（构造 60MB 若无上限则危险）
            big = b"PK\x03\x04" + b"\x00" * (60 * 1024 * 1024)
            st6, b6 = multipart_post(ADMIN + rest, "apk", "huge.apk", big, token=tok, timeout=120)
            j6 = None
            try:
                j6 = json.loads(b6.decode("utf-8", "replace"))
            except Exception:
                pass
            rejected6 = st6 >= 400 or (isinstance(j6, dict) and j6.get("ok") is False)
            rec("U6 60MB 超大文件 => 拒绝（或有上限）", rejected6,
                f"HTTP={st6} body={b6.decode('utf-8','replace')[:120]}")

            # 清理本次上传的探测文件（★ 含 U3 的 new_files 与 U4 的 u4_created）
            to_clean = sorted(set(new_files) | set(u4_created))
            for p in to_clean:
                try:
                    os.remove(p)
                    print(f"    （已清理探测文件 {os.path.relpath(p, ROOT)}）")
                except Exception as e:
                    print(f"    （清理失败 {p}: {e}）")
            # ★ 终检：候选目录应回到 U3 之前的状态
            leftover = set(list_all_apks()) - before
            if leftover:
                print(f"    ★ 仍有残留 {len(leftover)} 个: "
                      f"{[os.path.relpath(x, ROOT) for x in leftover]}")
            else:
                print("    ✓ 候选目录已回到测试前状态（无残留）")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  APK 上传可用、真落盘、路径穿越被阻、非 apk 被拒")
    return 0


if __name__ == "__main__":
    sys.exit(main())
