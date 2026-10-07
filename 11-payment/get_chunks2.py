import sys, json, io, re, os, urllib.request, ssl
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HOST = "merchant.lamuzhifu.top"
BASE = "https://" + HOST
PROXY = "http://127.0.0.1:10809"
OUT = r"E:\IOSusdt\chunks"
os.makedirs(OUT, exist_ok=True)

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
op = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}),
    urllib.request.HTTPSHandler(context=ctx))

CHUNKS = [
    "chunk-2d0b9f39.0651040c.js",
    "chunk-2d0c4e42.295a0d9f.js",
    "chunk-2d0e95df.fc38d2bc.js",
    "chunk-2d21f097.89ba1e86.js",
    "chunk-aaf22cd8.66592598.js",
    "chunk-b443f5b6.f2ac8f06.js",
]
mainpaths = set(re.findall(r'["\'](/api/[A-Za-z0-9_/]+)["\']',
               open(r"E:\IOSusdt\app_bundle.js", encoding="utf-8", errors="replace").read()))
allpaths = set(mainpaths)

for c in CHUNKS:
    try:
        r = op.open(urllib.request.Request(
            BASE + "/" + c,
            headers={"User-Agent": "Mozilla/5.0 Chrome/131.0.0.0 Safari/537.36",
                     "Referer": BASE + "/dashboard"}), timeout=30)
        txt = r.read().decode("utf-8", "replace")
    except Exception as e:
        print(f"  ERR {c}: {e}")
        continue
    open(os.path.join(OUT, c), "w", encoding="utf-8", errors="replace").write(txt)
    paths = set(re.findall(r'["\'](/api/[A-Za-z0-9_/]+)["\']', txt))
    allpaths |= paths
    role = re.findall(r'role:\s*(\d+)', txt)
    print(f"  200 {c:36s} {len(txt):7d}B api={len(paths):3d} roles={sorted(set(role))}")

print(f"\n[*] TOTAL unique /api/ paths: {len(allpaths)}")
extra = sorted(allpaths - mainpaths)
print(f"\n[*] NEW paths vs main bundle ({len(extra)}):")
for p in extra:
    print("   ", p)

print("\n[*] FULL LIST:")
for p in sorted(allpaths):
    print("   ", p)

json.dump(sorted(allpaths), open(r"E:\IOSusdt\all_apis.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n[+] all_apis.json saved")
