import sys, json, io, re, base64, urllib.request, ssl, http.cookiejar
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HOST = "merchant.lamuzhifu.top"
BASE = "https://" + HOST
PROXY = "http://127.0.0.1:10809"

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}),
    urllib.request.HTTPSHandler(context=ctx),
    urllib.request.HTTPCookieProcessor(cj))


def get(path, hd=None):
    h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"}
    if hd: h.update(hd)
    try:
        r = op.open(urllib.request.Request(BASE + path, headers=h), timeout=25)
        return r.status, r.read().decode("utf-8", "replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), dict(e.headers)
    except Exception as e:
        return -1, f"{type(e).__name__}: {e}", {}


print("=" * 74)
print("1) Discover admin / agent entry points")
print("=" * 74)
CANDIDATES = [
    "/admin", "/admin/login", "/manage", "/manager", "/backend", "/console",
    "/system", "/sys", "/agent", "/agent/login", "/agency", "/operator",
    "/root", "/super", "/cp", "/dashboard", "/admin/index.html",
    "/api/Admin/Login", "/api/admin/login", "/api/Admin/Self",
    "/api/Agent/Login", "/api/Agent/Self", "/api/System/AdminLogin",
]
for p in CANDIDATES:
    st, body, hdrs = get(p)
    tag = ""
    if st == 200:
        low = body.lower()
        if "<!doctype html" in low or "<html" in low:
            tag = "HTML app shell"
            m = re.search(r"<title>(.*?)</title>", body, re.S | re.I)
            if m: tag += f" title={m.group(1).strip()[:40]}"
        else:
            tag = body[:120]
    elif st == 402:
        tag = "SPRING: no mapping"
    elif st == 401:
        tag = "401 (exists, needs auth)"
    elif st == 403:
        tag = "403"
    print(f"  {st:>4}  {p:32s} {tag[:90]}")
