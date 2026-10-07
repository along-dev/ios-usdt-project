import sys, json, io, re, urllib.request, ssl
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HOST = "merchant.lamuzhifu.top"
BASE = "https://" + HOST
PROXY = "http://127.0.0.1:10809"
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
op = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}),
    urllib.request.HTTPSHandler(context=ctx))


def get(path):
    try:
        r = op.open(urllib.request.Request(
            BASE + path,
            headers={"User-Agent": "Mozilla/5.0 Chrome/131.0.0.0 Safari/537.36",
                     "Accept": "*/*", "Referer": BASE + "/login"}), timeout=30)
        return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return -1, str(e).encode()


# ---- 1) enumerate lazy chunks and search for admin-only routes ----
chunks = [l.strip() for l in open(r"E:\IOSusdt\chunklist.txt", encoding="utf-8")
          if l.strip().endswith(".js")]
print(f"[*] probing {len(chunks)} lazy chunks\n")

allpaths = set()
admin_hits = []
for c in chunks:
    st, body = get("/static/" + c)
    if st != 200:
        print(f"  {st:>4} {c}")
        continue
    txt = body.decode("utf-8", "replace")
    paths = set(re.findall(r'["\'](/api/[A-Za-z0-9_/]+)["\']', txt))
    allpaths |= paths
    isadmin = bool(re.search(r'admin|Admin|后台|总台', txt))
    print(f"  200  {c:36s} {len(txt):7d}B api={len(paths):3d} adminish={isadmin}")
    if isadmin:
        admin_hits.append((c, txt))

print(f"\n[*] union of /api/ paths across chunks: {len(allpaths)}")
new = sorted(allpaths - set(re.findall(r'["\'](/api/[A-Za-z0-9_/]+)["\']',
             open(r"E:\IOSusdt\app_bundle.js", encoding="utf-8", errors="replace").read())))
print("[*] paths NOT in the main bundle:")
for p in new:
    print("   ", p)

print("\n[*] admin-ish strings in chunks:")
for c, txt in admin_hits[:5]:
    for m in re.finditer(r'.{60}(admin|Admin|后台).{60}', txt):
        print(f"   [{c}] ...{m.group(0)}...")
        break
