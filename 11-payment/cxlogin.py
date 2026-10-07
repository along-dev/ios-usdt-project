"""
Full authenticated login against merchant.lamuzhifu.top.

Chain (reverse engineered from app.20075d53 + cx.v57.wasm):
  1. GET  /login                            -> server_name_session cookie
  2. open wss://host/cxw?s=<sid>            -> solve JS challenge -> X.w = 1
  3. POST /api/Account/Ping {ips,sid,t:"m"} -> __cxp = 1
  4. POST /api/Account/Login  (WASM envelope)
        headers: X-Ch: 1, X-Ck: <q(5) token>, X-Ws: <sid>
        body   : {v:3, k, p, q, t}  produced by WASM q(1)
  5. response {v:3,p,q,t} -> WASM q(2/_o(88)) decode path
"""
import sys, os, ssl, json, base64, asyncio, urllib.request, http.cookiejar
sys.path.insert(0, r"E:\IOSusdt")

import wasm_interp as wi
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes, serialization
import cxws

HOST = "merchant.lamuzhifu.top"
BASE = f"https://{HOST}"
PROXY = "http://127.0.0.1:10809"


def _o(m):
    return (m ^ 90) & 15


class Cx:
    """WASM oracle + HTTP client sharing one session."""

    def __init__(self):
        self.m = wi.load_module(r"E:\IOSusdt\cx_decoded.wasm")
        self.inst = wi.Instance(self.m, host_log=lambda x: None)
        for o, seg in self.m.data_segments:
            if o is not None:
                self.inst.mem[o:o + len(seg)] = seg
        self.q = self.m.exports["q"][1]
        self.inst.max_steps = 50_000_000
        self.B = self.inst.invoke(self.q, [_o(90), 0, 0, 0, 0, 0])
        self.pub = serialization.load_der_public_key(
            open(r"E:\IOSusdt\rsa_pub.der", "rb").read())
        self.cj = http.cookiejar.CookieJar()
        proxy = urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.op = urllib.request.build_opener(
            proxy, urllib.request.HTTPSHandler(context=ctx),
            urllib.request.HTTPCookieProcessor(self.cj))
        self.aes_key = None
        self.wp = None
        self.xck = None
        self.token = None

    # ---------- WASM primitives ----------
    def fingerprint(self, ff=0):
        self.inst.invoke(self.q, [_o(89), 1920, 1920, 1080, 1080, ff])

    def new_keys(self):
        self.aes_key = AESGCM.generate_key(bit_length=256)
        self.wp = self.pub.encrypt(
            self.aes_key,
            padding.OAEP(mgf=padding.MGF1(hashes.SHA1()),
                         algorithm=hashes.SHA1(), label=None))
        self.fingerprint()
        self.inst.mem[self.B + 64:self.B + 64 + 256] = self.wp
        n = self.inst.invoke(self.q, [_o(95), 256, 0, 0, 0])
        self.xck = "".join(
            chr(self.inst.mem[self.B + 31522816 + i]) for i in range(n))
        return self.xck

    def envelope(self, obj):
        """encrypt(): AES-256-GCM + RSA-OAEP(wrapped key) -> {v,k,p,q,t}"""
        if self.aes_key is None:
            self.new_keys()
        pt = json.dumps(obj, ensure_ascii=False).encode()
        iv = os.urandom(12)
        rnd = os.urandom(8)
        ct = AESGCM(self.aes_key).encrypt(iv, pt, None)
        self.fingerprint()
        self.inst.mem[self.B + 0:self.B + 32] = self.aes_key
        self.inst.mem[self.B + 64:self.B + 64 + 256] = self.wp
        self.inst.mem[self.B + 400:self.B + 412] = iv
        self.inst.mem[self.B + 416:self.B + 424] = rnd
        self.inst.mem[self.B + 1024:self.B + 1024 + len(ct)] = ct
        n = self.inst.invoke(self.q, [_o(91), len(ct), 256, 0, 0])
        s = "".join(chr(self.inst.mem[self.B + 31522816 + i]) for i in range(n))
        return json.loads(s)

    def decode(self, resp):
        """Run the server response through the WASM decode path.

        decrypt() in the bundle feeds  p+q  into q(_o(88)), takes the returned
        length, then AES-GCM-decrypts the slice at B+1024 with the IV at B+400.
        We replicate the WASM side and then try the AES-GCM step.
        """
        enc = str(resp.get("p") or "") + str(resp.get("q") or "")
        self.fingerprint()
        self.inst.mem[self.B + 0:self.B + 32] = self.aes_key
        for i in range(len(enc)):
            self.inst.mem[self.B + 10551296 + i] = ord(enc[i]) & 255
        cl = self.inst.invoke(self.q, [_o(88), len(enc), 0, 0, 0])
        iv = bytes(self.inst.mem[self.B + 400:self.B + 412])
        ct = bytes(self.inst.mem[self.B + 1024:self.B + 1024 + cl])
        for label, key, ivc, ctc in (
                ("wasm-iv", self.aes_key, iv, ct),
                ("raw", self.aes_key, iv, ct)):
            try:
                return json.loads(AESGCM(key).decrypt(ivc, ctc, None).decode())
            except Exception:
                pass
        return {"_undecoded": True, "cl": cl, "iv": iv.hex(), "ct": ct[:64].hex()}

    # ---------- HTTP ----------
    def _req(self, path, data=None, headers=None, method=None):
        hd = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
              "Origin": BASE, "Referer": BASE + "/login",
              "Accept": "application/json, text/plain, */*"}
        if headers:
            hd.update(headers)
        body = None
        if data is not None:
            body = json.dumps(data).encode()
            hd.setdefault("Content-Type", "application/json")
        req = urllib.request.Request(BASE + path, data=body, headers=hd,
                                     method=method or ("POST" if body else "GET"))
        try:
            r = self.op.open(req, timeout=30)
            return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")
        except Exception as e:
            return -1, f"{type(e).__name__}: {e}"

    def get_login_page(self):
        return self._req("/login", method="GET")

    def ping(self, sid, ips=None):
        return self._req("/api/Account/Ping",
                         {"ips": ips or [], "sid": sid, "t": "m"})

    def login(self, name, pwd, totp="", sid="0"):
        body = self.envelope({"LoginName": name, "Password": pwd, "Totp": totp})
        hd = {"Content-Type": "application/json", "X-Ch": "1",
              "X-Ck": self.xck, "X-Ws": sid}
        st, txt = self._req("/api/Account/Login", data=body, headers=hd)
        return st, txt


async def do_login():
    cx = Cx()
    sid = str(10000000 + int.from_bytes(os.urandom(3), "big") % 90000000)

    st, _ = cx.get_login_page()
    print(f"[1] GET /login                 -> {st}  cookies={[c.name for c in cx.cj]}")

    # 2. WS challenge in the background while we proceed
    ready = asyncio.Event()
    holder = {}

    async def on_open(state):
        holder["state"] = state
        st_, _ = cx.ping(sid)
        print(f"[3] POST /api/Account/Ping     -> {st_}  (sid={sid})")
        holder["ping"] = st_
        ready.set()

    ws_task = asyncio.create_task(
        cxws.run_challenge_session(sid, on_open=on_open, hold_seconds=40, verbose=True))
    try:
        await asyncio.wait_for(ready.wait(), timeout=25)
    except asyncio.TimeoutError:
        print("[!] WS never opened")
    await asyncio.sleep(2)

    st, txt = cx.login("冠军", "<REDACTED_PASSWORD>", "", sid=sid)
    print(f"[4] POST /api/Account/Login    -> {st}")
    print(f"    raw: {txt[:300]}")
    if st == 200:
        try:
            resp = json.loads(txt)
            if "p" in resp:
                out = cx.decode(resp)
                print(f"    decoded: {json.dumps(out, ensure_ascii=False)[:600]}")
        except Exception as e:
            print("    decode err:", e)
    try:
        await asyncio.wait_for(ws_task, timeout=5)
    except Exception:
        pass
    print("[5] WS state:", holder.get("state").__dict__ if holder.get("state") else None)


if __name__ == "__main__":
    asyncio.run(do_login())
