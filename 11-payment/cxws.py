"""
cxw WebSocket challenge solver for merchant.lamuzhifu.top

Protocol (recovered from /static/app.20075d53 + WASM dynamic JS):
  1. Open  wss://<host>/cxw?s=<sid>
  2. Server sends a JS snippet; client must eval it with bindings (w, X)
     and return the result string as the next WS frame.
  3. Challenge form observed:
        var s="<digits>",n=3000,i=0,x=0;
        for(;i<n;i++)x=((x<<5)-x+s.charCodeAt(i%s.length)+i)|0;
        if(X)X.w=1;
        return (x>>>0).toString(16);
     -> emulate locally, set X.w=1, send hex digest back.
  4. Client then POSTs /api/Account/Ping {ips,sid,t} -> window.__cxp = 1
  5. Only when X.w==1 AND __cxp==1 does the frontend send the encrypted
     POST /api/Account/Login.
"""
import asyncio, ssl, json, re, os, sys, time
import websockets
from websockets.asyncio.client import connect

HOST = "merchant.lamuzhifu.top"
PROXY = "http://127.0.0.1:10809"


class ChallengeState:
    def __init__(self):
        self.w = 0          # X.w  -- set to 1 by a successful challenge
        self.pinged = 0     # __cxp


def eval_challenge(code, st: ChallengeState):
    """Emulate the server-supplied JS challenge without a JS engine.

    Supported shapes (all observed variants are small arithmetic digests):
        var s="...", n=N, i=0, x=0;
        for(;i<n;i++) x = ((x<<5)-x + s.charCodeAt(i%s.length) + i)|0;
        return (x>>>0).toString(16);
    """
    m = re.search(r'var\s+s\s*=\s*"([^"]*)"', code)
    if not m:
        return None
    s = m.group(1)
    mn = re.search(r'\bn\s*=\s*(\d+)', code)
    n = int(mn.group(1)) if mn else 3000
    # detect the shift/add digest constants
    msh = re.search(r'\(\(x<<(\d+)\)\s*-\s*x\s*\+\s*s\.charCodeAt', code)
    shift = int(msh.group(1)) if msh else 5
    x = 0
    for i in range(n):
        v = (x << shift) - x + ord(s[i % len(s)]) + i
        # emulate JS `|0` 32-bit signed truncation
        v &= 0xFFFFFFFF
        if v >= 0x80000000:
            v -= 0x100000000
        x = v
    xu = x & 0xFFFFFFFF
    if "toString(16)" in code:
        out = format(xu, "x")
    elif "toString(2)" in code:
        out = format(xu, "b")
    elif "toString(36)" in code:
        digits = "0123456789abcdefghijklmnopqrstuvwxyz"
        out = ""
        v = xu
        while v:
            out = digits[v % 36] + out
            v //= 36
        out = out or "0"
    else:
        out = str(xu)
    if "if(X)X.w=1" in code or "X.w=1" in code:
        st.w = 1
    return out


async def run_challenge_session(sid: str, on_open=None, hold_seconds=45, verbose=True):
    """Open the cxw WS, solve every challenge, keep the session alive."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    st = ChallengeState()
    url = f"wss://{HOST}/cxw?s={sid}"
    hdrs = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
        "Origin": f"https://{HOST}",
    }
    solved = []
    async with connect(url, ssl=ctx, additional_headers=hdrs,
                       open_timeout=25, proxy=PROXY) as ws:
        if verbose:
            print(f"[ws] connected {url}")
        if on_open:
            await on_open(st)

        async def keepalive():
            while True:
                await asyncio.sleep(10)
                try:
                    await ws.send("1")
                except Exception:
                    return

        ka = asyncio.create_task(keepalive())
        deadline = time.time() + hold_seconds
        try:
            while time.time() < deadline:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=max(1, deadline - time.time()))
                except asyncio.TimeoutError:
                    break
                if isinstance(msg, bytes):
                    msg = msg.decode("utf-8", "replace")
                if verbose:
                    print(f"[ws] <<< {msg[:200]}")
                ans = eval_challenge(msg, st)
                if ans is not None:
                    solved.append(ans)
                    if verbose:
                        print(f"[ws] >>> {ans}   (X.w={st.w})")
                    await ws.send(ans)
        finally:
            ka.cancel()
    return st, solved


if __name__ == "__main__":
    sid = sys.argv[1] if len(sys.argv) > 1 else "82412345"
    st, solved = asyncio.run(run_challenge_session(sid, hold_seconds=int(sys.argv[2]) if len(sys.argv) > 2 else 20))
    print("challenges solved:", solved, "X.w =", st.w)
