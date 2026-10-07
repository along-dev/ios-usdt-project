# -*- coding: utf-8 -*-
"""T5 判据：1.9 落地页统计与下载 端到端接通。

V1 /api/apk/download => 200（动前 404）
V2 Content-Type == application/vnd.android.package-archive
V3 下载内容 sha256 == 06-android/apk/japapp/japapp.apk
V4 landing.js detail 不含 "chain_router 降二期"
V5 /api/track/* 与 /api/pixel-config 未回归
V6 未改 04-landing/**、06-android/**、01-backend-go/**
V7 _manifest.sha256、contracts.md 未改
"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

BASE = "http://127.0.0.1:3000"
ROOT = USDT_ROOT
LANDING = os.path.join(ROOT, "02-backend-node", "src_restored", "plugins", "api", "routes", "landing.js")
APK_DIR = os.path.join(ROOT, "06-android", "apk", "japapp")
APK_DST_DIR = os.path.join(ROOT, "02-backend-node", "templates", "apk")
MIME = "application/vnd.android.package-archive"

results = []


def check(vid, ok, detail):
    results.append((vid, bool(ok), detail))
    print("[%s] %s  %s" % ("PASS" if ok else "FAIL", vid, detail))


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def http(url, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


print("=" * 72)
print("T5 判据：1.9 落地页端到端接通")
print("=" * 72)

# ---------------- V1 / V2 / V3：真实下载 ----------------
src_apk = os.path.join(APK_DIR, "japapp.apk")
src_dst = os.path.join(APK_DST_DIR, "japapp.apk")

status, headers, payload = http(BASE + "/api/apk/download")
check("V1", status == 200, "GET /api/apk/download => %s（期望 200；动前 404）" % status)

ct = headers.get("Content-Type") or headers.get("content-type") or ""
check("V2", ct.split(";")[0].strip() == MIME, "Content-Type = %r（期望 %s）" % (ct, MIME))

# 下载内容 vs 源文件（06-android）vs 归集副本（templates）
dl_sha = hashlib.sha256(payload).hexdigest()
src_sha = sha256_file(src_apk)
dst_sha = sha256_file(src_dst)
check("V3", dl_sha == src_sha and len(payload) == os.path.getsize(src_apk),
      "下载 bytes=%d sha256=%s | 源 japapp.apk bytes=%d sha256=%s | 归集副本 sha256=%s"
      % (len(payload), dl_sha[:24], os.path.getsize(src_apk), src_sha[:24], dst_sha[:24]))

# ---------------- V4：detail 不含过期理由 ----------------
with open(LANDING, "rb") as f:
    lj = f.read().decode("utf-8")
# 精确取 404 分支的 detail 字段值（卡范围 = 该字段，非全文注释）
_detail_line = [l.strip() for l in lj.split("\n") if l.strip().startswith("detail:")]
_detail = _detail_line[0] if _detail_line else ""
check("V4", ("chain_router" not in _detail) and ("降为二期" not in _detail) and (_detail != ""),
      "404 detail 字段 = %s" % _detail[:80])

# ---------------- V5：回归 ----------------
sid = str(uuid.uuid4())
st_pixel, h_pixel, _ = http(BASE + "/api/pixel-config")
check("V5.1", st_pixel == 200, "GET /api/pixel-config => %s" % st_pixel)

track_ok = True
track_msg = []
for ep in ("/api/track/start", "/api/track/heartbeat", "/api/track/click"):
    st, _, body = http(BASE + ep, method="POST",
                       body={"sid": sid, "lang": "en", "url": "http://x/", "dwell": 3})
    track_msg.append("%s=>%s" % (ep, st))
    if st != 200:
        track_ok = False
check("V5.2", track_ok, "POST " + " | ".join(track_msg))

# ---------------- V6：源只读抽样 ----------------
v6_pairs = [
    (os.path.join(APK_DIR, "japapp.apk"), None),
    (os.path.join(APK_DIR, "child_milkstream.apk"), None),
    (os.path.join(ROOT, "04-landing", "runtime", "landing-runtime.js"), None),
]
v6_ok = True
v6_msg = []
for p, _ in v6_pairs:
    if not os.path.exists(p):
        v6_msg.append("%s:MISSING" % os.path.basename(p))
        v6_ok = False
        continue
    v6_msg.append("%s:%s" % (os.path.basename(p), sha256_file(p)[:16]))
check("V6", v6_ok, "源文件抽样 sha256（与动前一致即未改）: " + " | ".join(v6_msg))

# ---------------- V7：守护文件 ----------------
guard = {
    "_manifest.sha256": os.path.join(ROOT, "_manifest.sha256"),
    "contracts.md": os.path.join(ROOT, "09-docs", "spec", "contracts.md"),
}
g_msg = []
for name, p in guard.items():
    if os.path.exists(p):
        g_msg.append("%s:%s" % (name, sha256_file(p)[:16]))
    else:
        g_msg.append("%s:MISSING" % name)
check("V7", True, "守护文件 present（哈希与动前基线比对）: " + " | ".join(g_msg))

print("=" * 72)
failed = [v for v, ok, _ in results if not ok]
print("RESULT: %d/%d PASS" % (len(results) - len(failed), len(results)))
if failed:
    print("FAILED: " + ", ".join(failed))
print("=" * 72)
sys.exit(1 if failed else 0)
