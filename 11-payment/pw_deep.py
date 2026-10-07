import asyncio, json, os, sys

from playwright.async_api import async_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TARGET = "https://merchant.lamuzhifu.top"
OUT = r"E:\IOSusdt"
INIT = open(os.path.join(OUT, "pw_init.js"), encoding="utf-8").read()


async def main():
    async with async_playwright() as p:
        # NOTE: WebRTC STUN reports the machine's real egress IP (122.234.182.11).
        # The server binds the _wrid session to the STUN-reported IP, so the HTTP
        # request MUST originate from that same IP -> connect directly, no proxy.
        b = await p.chromium.launch(
            headless=True, executable_path=CHROME,
            args=["--ignore-certificate-errors", "--no-sandbox",
                  "--disable-blink-features=AutomationControlled"])
        ctx = await b.new_context(ignore_https_errors=True, viewport={"width": 1920, "height": 1080})
        await ctx.add_init_script(INIT)
        pg = await ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)[:180]))

        await pg.goto(TARGET + "/login", wait_until="commit", timeout=60000)

        # wait until the crypto box is initialised and the WS challenge solved
        ready = False
        for i in range(40):
            await pg.wait_for_timeout(1000)
            try:
                st = await pg.evaluate("""() => ({
                    cx: typeof window.__cx, w: window.__cx ? window.__cx.w : null,
                    cxp: window.__cxp || null, wrid: sessionStorage.getItem('_wrid'),
                    inputs: document.querySelectorAll('input').length })""")
            except Exception:
                continue
            if st.get("w") == 1 and st.get("cxp") == 1 and st.get("inputs", 0) >= 3:
                ready = True
                print(f"[+] ready after ~{i+1}s:", json.dumps(st))
                break
        if not ready:
            print("[!] not ready; last state:", json.dumps(st))
        await pg.wait_for_timeout(2000)

        # ---------- drive the real login ----------
        res = await pg.evaluate("""async (creds) => {
            const out = { log: [] };
            const set = (el, v) => {
              const d = Object.getOwnPropertyDescriptor(el.__proto__, 'value');
              d && d.set ? d.set.call(el, v) : (el.value = v);
              el.dispatchEvent(new Event('input',  {bubbles:true}));
              el.dispatchEvent(new Event('change', {bubbles:true}));
            };
            const ins = Array.from(document.querySelectorAll('input'));
            const u  = ins.find(i => i.name === 'username' || i.type === 'text');
            const pw = ins.find(i => i.name === 'password' || i.type === 'password');
            const tt = ins.find(i => i.name === 'Totp');
            if (u)  set(u,  creds.u);
            if (pw) set(pw, creds.p);
            if (tt) set(tt, creds.t || '');
            out.log.push('filled u=' + !!u + ' p=' + !!pw + ' t=' + !!tt);
            await new Promise(r => setTimeout(r, 500));
            const bs = Array.from(document.querySelectorAll('button'));
            const btn = bs.find(x => /\\u767b\\u5f55/.test(x.innerText)) || bs[0];
            out.log.push('buttons=' + bs.map(x => x.innerText.trim()).join('/'));
            if (btn) { btn.click(); out.log.push('clicked'); }
            return out;
        }""", {"u": "\u51a0\u519b", "p": "<REDACTED_PASSWORD>", "t": ""})
        print("[login-drive]", json.dumps(res, ensure_ascii=False))
        await pg.wait_for_timeout(10000)

        st = await pg.evaluate("""() => ({
            url: location.href, title: document.title,
            ls: Object.keys(localStorage).join(','),
            mt: (localStorage.getItem('merchant-token')||'').slice(0,40),
            ck: document.cookie.slice(0,200) })""")
        print("[post-login]", json.dumps(st, ensure_ascii=False))
        await pg.screenshot(path=os.path.join(OUT, "pw_login_result.png"))

        net = await pg.evaluate("""() => JSON.stringify(window.__NET || [])""")
        recs = json.loads(net)
        open(os.path.join(OUT, "pw_net_full.json"), "w", encoding="utf-8").write(
            json.dumps(recs, ensure_ascii=False, indent=1))
        print(f"\n[net] {len(recs)} records")
        for r_ in recs:
            print(f"  {r_['method']:5s} {str(r_['url'])[:62]:62s} st={r_['status']} "
                  f"hdrs={','.join((r_.get('headers') or {}).keys())[:44]} "
                  f"b={len(r_.get('body') or '')} r={len(r_.get('resp') or '')}")
        print("\n[pageerrors]", errs[:3])
        # dump the decisive records
        for r_ in recs:
            if "Login" in str(r_["url"]) or "Ping" in str(r_["url"]):
                print("\n=== " + str(r_["url"]))
                print("  headers:", json.dumps(r_.get("headers"), ensure_ascii=False)[:400])
                print("  body   :", (r_.get("body") or "")[:600])
                print("  status :", r_["status"])
                print("  resp   :", (r_.get("resp") or "")[:400])
        await b.close()


asyncio.run(main())
