import asyncio, json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.async_api import async_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TARGET = "https://merchant.lamuzhifu.top"
OUT = r"E:\IOSusdt"
INIT = open(os.path.join(OUT, "pw_init.js"), encoding="utf-8").read()

LOGIN = "\u51a0\u519b"
PASSWD = "<REDACTED_PASSWORD>"


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(
            headless=True, executable_path=CHROME,
            args=["--ignore-certificate-errors", "--no-sandbox",
                  "--disable-blink-features=AutomationControlled"])
        ctx = await b.new_context(ignore_https_errors=True,
                                  viewport={"width": 1920, "height": 1080})
        await ctx.add_init_script(INIT)
        pg = await ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)[:180]))

        await pg.goto(TARGET + "/login", wait_until="commit", timeout=60000)

        # Wait for crypto readiness AND for the STUN-bearing Ping to land.
        st = None
        for i in range(50):
            await pg.wait_for_timeout(1000)
            st = await pg.evaluate("""() => ({
                w: window.__cx ? window.__cx.w : null, cxp: window.__cxp || null,
                wrid: sessionStorage.getItem('_wrid'),
                inputs: document.querySelectorAll('input').length,
                stun: (window.__NET||[]).filter(x =>
                    String(x.url).indexOf('/api/Account/Ping') >= 0 &&
                    (x.body||'').indexOf('122.') >= 0).length })""")
            if st and st["w"] == 1 and st["cxp"] == 1 and st["stun"] >= 1 and st["inputs"] >= 3:
                print(f"[+] STUN Ping observed after ~{i+1}s:", json.dumps(st))
                break
        else:
            print("[!] timeout waiting; state:", json.dumps(st))
        await pg.wait_for_timeout(1500)

        res = await pg.evaluate("""async (c) => {
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
            if (u) set(u, c.u); if (pw) set(pw, c.p); if (tt) set(tt, c.t || '');
            await new Promise(r => setTimeout(r, 600));
            const bs = Array.from(document.querySelectorAll('button'));
            const btn = bs.find(x => /\\u767b\\u5f55/.test(x.innerText)) || bs[0];
            if (btn) btn.click();
            return { n: ins.length, clicked: !!btn };
        }""", {"u": LOGIN, "p": PASSWD, "t": ""})
        print("[drive]", json.dumps(res))
        await pg.wait_for_timeout(12000)

        after = await pg.evaluate("""() => ({
            url: location.href, title: document.title,
            ls: Object.keys(localStorage).join(','),
            tokens: ['merchant-token','admtoken','supplier-token','token']
                       .map(k => k + '=' + ((localStorage.getItem(k)||'').slice(0,24) || '-')).join(' '),
            ck: document.cookie.slice(0, 200) })""")
        print("[after]", json.dumps(after, ensure_ascii=False))
        await pg.screenshot(path=os.path.join(OUT, "pw_login_result.png"), full_page=True)

        recs = json.loads(await pg.evaluate("() => JSON.stringify(window.__NET||[])"))
        open(os.path.join(OUT, "pw_net_full.json"), "w", encoding="utf-8").write(
            json.dumps(recs, ensure_ascii=False, indent=1))
        print(f"\n[net] {len(recs)}")
        for r_ in recs:
            body = (r_.get("resp") or "")
            try:
                msg = json.loads(body).get("Message", "")
            except Exception:
                msg = body[:120]
            print(f"  {r_['method']:5s} {str(r_['url'])[:58]:58s} st={r_['status']} "
                  f"r={len(body)} msg={msg}")
        print("\n[errs]", errs[:3])
        await b.close()


asyncio.run(main())
