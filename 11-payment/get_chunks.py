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


# collect chunk ids referenced in the bundle
s = open(r"E:\IOSusdt\app_bundle.js", encoding="utf-8", errors="replace").read()
ids = sorted(set(re.findall(r'chunk-[0-9a-f]{8}', s)))
print(f"[*] {len(ids)} chunk ids referenced in bundle\n")

mainpaths = set(re.findall(r'["\'](/api/[A-Za-z0-9_/]+)["\']', s))
allpaths = set(mainpaths)
ok = 0
for cid in ids:
    st, body = get("/" + cid + ".js")
    if st != 200:
        continue
    ok += 1
    txt = body.decode("utf-8", "replace")
    open(os.path.join(OUT, cid + ".js"), "w", encoding="utf-8", errors="replace").write(txt)
    paths = set(re.findall(r'["\'](/api/[A-Za-z0-9_/]+)["\']', txt))
    allpaths |= paths

print(f"[*] downloaded {ok}/{len(ids)} chunks -> {OUT}")
print(f"\n[*] TOTAL unique /api/ paths: {len(allpaths)}\n")

extra = sorted(allpaths - mainpaths)
print(f"[*] paths NEW vs main bundle ({len(extra)}):")
for p in extra:
    print("   ", p)

print("\n[*] full merged list:")
for p in sorted(allpaths):
    print("   ", p)

json.dump(sorted(allpaths), open(r"E:\IOSusdt\all_apis.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
