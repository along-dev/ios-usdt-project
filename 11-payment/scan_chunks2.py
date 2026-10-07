import re, io, sys, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

D = r"E:\IOSusdt\chunks"
CH = ["chunk-2d0b9f39.0651040c.js", "chunk-2d0c4e42.295a0d9f.js",
      "chunk-2d0e95df.fc38d2bc.js", "chunk-2d21f097.89ba1e86.js",
      "chunk-aaf22cd8.66592598.js", "chunk-b443f5b6.f2ac8f06.js"]
allp = set()
for c in CH:
    p = os.path.join(D, c)
    if not os.path.exists(p):
        continue
    t = open(p, encoding="utf-8", errors="replace").read()
    # any occurrence of /api or api/ fragments
    frags = re.findall(r'["\']((?:/api/|\w+/)[A-Za-z0-9_/]{2,})["\']', t)
    api = sorted(set(f for f in frags if "api" in f.lower() or "/List" in f or
                     "/Login" in f or "/Export" in f or "Dashboard" in f))
    print(f"\n=== {c} ({len(t)}B)")
    if api:
        for a in api:
            print("   ", a)
    allp |= set(api)
    # show quoted strings that look like endpoint tails
    tails = sorted(set(re.findall(r'["\']([A-Z][A-Za-z]{2,20}(?:/[A-Za-z]+)?)["\']', t)))
    print("   tails:", ", ".join(tails[:40]))

print("\n[*] union:", len(allp))
for a in sorted(allp):
    print("   ", a)
