import asyncio, json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.async_api import async_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TARGET = "https://merchant.lamuzhifu.top"
OUT = r"E:\IOSusdt"
INIT = open(os.path.join(OUT, "pw_init_clean.js"), encoding="utf-8").read()
PROXY = "http://127.0.0.1:10809"
LOGIN, PASSWD = "\u51a0\u519b", "<REDACTED_PASSWORD>"

ROUTES = [
    "/dashboard",
    "/AccountManagement/LoginManagement",
    "/fund/FundDetails",
    "/fund/RechargeRecord",
    "/Pay/payInOrderList",
    "/Pay/payOutOrderList",
    "/MerchantOrderList",
    "/CommissionList",
    "/DailyReport",
    "/ApiKeyManagement",
    "/IP",
    "/Channels",
]


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(
            headless=False, executable_path=CHROME,
            proxy={"server": PROXY},
            args=["--ignore-certificate-errors", "--no-sandbox",
                  "--disable-blink-features=AutomationControlled",
                  "--window-size=1920,1080"])
        ctx = await b.new_context(ignore_https_errors=True,
                                  viewport={"width": 1920, "height": 1080},
                                  screen={"width": 1920, "height": 1080})
        await ctx.add_init_script(INIT)
        pg = await ctx.new_page()

        await pg.goto(TARGET + "/login", wait_until="commit", timeout=60000)
        for i in range(40):
            await pg.wait_for_timeout(1000)
            try:
                d = await pg.evaluate("""() => ({ w: window.__cx?window.__cx.w:null,
                    cxp: window.__cxp||null, inputs: document.querySelectorAll('input').length,
                    ow: window.outerWidth })""")
            except Exception:
                continue
            if d and d["w"] == 1 and d["cxp"] == 1 and d["inputs"] >= 3 and d.get("ow", 0) > 0:
                print(f"[ready ~{i+1}s] {json.dumps(d)}")
                break
        await pg.wait_for_timeout(2000)

        await pg.evaluate("""async (c) => {
            const set=(el,v)=>{const d=Object.getOwnPropertyDescriptor(el.__proto__,'value');
              d&&d.set?d.set.call(el,v):(el.value=v);
              el.dispatchEvent(new Event('input',{bubbles:true}));
              el.dispatchEvent(new Event('change',{bubbles:true}));};
            const ins=Array.from(document.querySelectorAll('input'));
            const u=ins.find(i=>i.name==='username'||i.type==='text');
            const pw=ins.find(i=>i.name==='password'||i.type==='password');
            const tt=ins.find(i=>i.name==='Totp');
            if(u)set(u,c.u); if(pw)set(pw,c.p); if(tt)set(tt,'');
            await new Promise(r=>setTimeout(r,900));
            const bs=Array.from(document.querySelectorAll('button'));
            const btn=bs.find(x=>/\\u767b\\u5f55/.test(x.innerText))||bs[0];
            if(btn)btn.click(); }""", {"u": LOGIN, "p": PASSWD})

        # wait for a token to appear in localStorage
        tok = ""
        for i in range(45):
            await pg.wait_for_timeout(1000)
            try:
                tok = await pg.evaluate("() => localStorage.getItem('merchant-token') || ''")
                if tok:
                    print(f"[+] LOGIN OK after ~{i+1}s; token len={len(tok)}")
                    break
            except Exception:
                continue
        if not tok:
            cur = await pg.evaluate("() => location.href")
            print(f"[!] no token; url={cur}")
            await b.close()
            return

        auth = await pg.evaluate("""() => ({ token: localStorage.getItem('merchant-token'),
            userInfo: localStorage.getItem('userInfo'),
            keys: Object.keys(localStorage).join(',') })""")
        open(os.path.join(OUT, "token.json"), "w", encoding="utf-8").write(
            json.dumps(auth, ensure_ascii=False, indent=1))
        print("[AUTH] token saved; keys:", auth["keys"])

        # Navigate the SPA so its own axios interceptors issue the requests
        for route in ROUTES:
            try:
                await pg.goto(TARGET + route, wait_until="commit", timeout=40000)
                await pg.wait_for_timeout(5000)
            except Exception as e:
                print(f"  {route:40s} nav-warn {str(e)[:50]}")
            recs = await pg.evaluate("() => JSON.stringify((window.__NET||[]).filter(x => String(x.url).indexOf('/api/')>=0))")
            arr = json.loads(recs)
            api = [x for x in arr if "/api/" in str(x["url"])]
            ok = sum(1 for x in api if x.get("status") == 200 and len(x.get("resp") or "") > 100)
            print(f"  {route:42s} api={len(api):3d} ok200={ok:3d}")

        allrec = json.loads(await pg.evaluate("() => JSON.stringify(window.__NET||[])"))
        open(os.path.join(OUT, "pw_fund_net.json"), "w", encoding="utf-8").write(
            json.dumps(allrec, ensure_ascii=False, indent=1))
        print(f"\n[+] saved pw_fund_net.json ({len(allrec)} records)")
        seen = {}
        for r_ in allrec:
            u = str(r_["url"]).split("?")[0]
            if "/api/" in u:
                seen.setdefault(u, r_)
        print("\n[API endpoints reached]")
        for u, r_ in sorted(seen.items()):
            print(f"  {r_['method']:5s} {u:48s} st={r_['status']} r={len(r_.get('resp') or '')}")
        await pg.screenshot(path=os.path.join(OUT, "pw_dashboard.png"), full_page=True)
        await b.close()


asyncio.run(main())
