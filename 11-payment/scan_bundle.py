import re, io, sys, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

s = open(r"E:\IOSusdt\app_bundle.js", encoding="utf-8", errors="replace").read()
print("bundle len", len(s))

print("\n--- role / auth tokens ---")
for kw in ["systemMode", "admin-token", "admtoken", "supplier-token", "merchant-token",
           "isAdmin", "AdminLogin", "AgentLogin", "type:", "role"]:
    print(f"  {kw:18s} {len(re.findall(re.escape(kw), s))}")

print("\n--- ALL /api/ paths in main bundle ---")
apis = sorted(set(re.findall(r'["\'](/api/[A-Za-z0-9_/]+)["\']', s)))
print("count:", len(apis))
for a in apis:
    print("  ", a)

print("\n--- lazy chunk list ---")
try:
    cl = open(r"E:\IOSusdt\chunklist.txt", encoding="utf-8").read()
    print(cl)
except Exception as e:
    print("err", e)

print("\n--- any admin-ish strings ---")
for kw in ["admin", "Admin", "后台", "总后台", "代理", "Agent", "agency"]:
    hits = [m.start() for m in re.finditer(re.escape(kw), s)][:6]
    print(f"  {kw:10s} {len(hits)} sample offsets {hits}")
