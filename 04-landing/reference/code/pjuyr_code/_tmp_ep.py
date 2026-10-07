import re,sys,io
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
h=open("admin_dashboard.html",encoding="utf-8",errors="replace").read()
print("LEN",len(h))
print("=== paths ===\n")
eps=set(re.findall(r"['\"`](/[A-Za-z0-9_\-./]{2,60})['\"`]",h))
for e in sorted(eps): print("  ",e)
print("=== urls ===\n")
for u in sorted(set(re.findall(r"https?://[A-Za-z0-9._\-]+[A-Za-z0-9_/.\-?=&%]*",h))): print("  ",u)
