import re,sys,io
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
h=open("admin_dashboard.html",encoding="utf-8",errors="replace").read()
# The dashboard is html+js; print the script portion
m=re.findall(r"<script[^>]*>(.*?)</script>",h,re.S|re.I)
print("script blocks:",len(m))
for i,s in enumerate(m):
    print(f"--- block {i} ({len(s)}b) ---")
    print(s[:6000])
