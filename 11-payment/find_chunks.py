import re, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

s = open(r"E:\IOSusdt\app_bundle.js", encoding="utf-8", errors="replace").read()
o = open(r"E:\IOSusdt\login.html", encoding="utf-8", errors="replace").read()

print("=== chunk path helpers in bundle ===")
for pat in [r'static/[^"\']*', r'\.js["\']', r'__webpack_require__\.p\s*=', r'p\s*=\s*["\'][^"\']*["\']']:
    for m in list(re.finditer(pat, s))[:8]:
        print(f"  [{pat}] {m.group(0)[:120]}")

print("\n=== script/link tags in login.html ===")
for m in re.finditer(r'<(script|link)[^>]*>', o):
    print("  ", m.group(0)[:200])

print("\n=== chunk id -> filename map (webpack) ===")
for m in list(re.finditer(r'\{\s*\d+\s*:\s*"[0-9a-f]{8}"[^}]{0,400}\}', s))[:4]:
    print("  ", m.group(0)[:400])

print("\n=== any 'chunk-' string ===")
for m in list(re.finditer(r'chunk-[0-9a-f]+[^"\']*', s))[:10]:
    print("  ", m.group(0)[:120])

print("\n=== hunt admin/agent front-end entry ===")
for kw in ["AgentLogin", "agent", "Agency", "总后台", "后台管理", "运营"]:
    for m in list(re.finditer(re.escape(kw), s))[:3]:
        a = max(0, m.start() - 120)
        print(f"  [{kw}] ...{s[a:m.start()+160]}...".replace("\n", " "))
        print()
