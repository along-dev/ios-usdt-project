import asyncio, json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.async_api import async_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TARGET = "https://merchant.lamuzhifu.top"
OUT = r"E:\IOSusdt"
INIT = open(os.path.join(OUT, "pw_init_clean.js"), encoding="utf-8").read()
PROXY = "http://127.0.0.1:10809"
LOGIN, PASSWD = "\u51a0\u519b", "<REDACTED_PASSWORD>"

PAGER = lambda cond=None: {"Pager": {"PageIndex": 1, "PageSize": 50}, "Condition": cond or {}}

POSTS = [
    ("/api/Transaction/List", PAGER()),
    ("/api/BalanceRecord/List", PAGER()),
    ("/api/MerchantOrder/List", PAGER()),
    ("/api/CommissionSettlement/List", PAGER()),
    ("/api/Commission/List", PAGER()),
    ("/api/MerchantDailyReport/List", PAGER()),
    ("/api/CommissionSettlement/Balance", {}),
    ("/api/WebOrder/ApplyWithdrawalOrders", PAGER()),
    ("/api/Agent/Subordinates", PAGER()),
    ("/api/AgentDailyReport/List", PAGER()),
    ("/api/AgentReviewMerchantOrderList/List", PAGER()),
    ("/api/RechargeRecord/List", PAGER()),
    ("/api/FundDetails/List", PAGER()),
    ("/api/Withdrawal/List", PAGER()),
    ("/api/PayInOrder/List", PAGER()),
    ("/api/PayOutOrder/List", PAGER()),
]

GETS = [
    "/api/Account/Self",
    "/api/Home/Dashboard",
    "/api/ApiKey/List",
    "/api/AuthorizedIp/List",
    "/api/System/Settings",
    "/api/MerchantChannel/List",
    "/api/Account/GenerateTwoFactorKey",
]


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(
            headless=False, executable_path=CHROME, proxy={"server": PROXY},
            args=["--ignore-certificate-errors", "--no-sandbox",
                  "--disable-blink-features=AutomationControlled", "--window-size=1920,1080"])
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
                    cxp: window.__cxp||null, n: document.querySelectorAll('input').length })""")
            except Exception:
                continue
            if d and d["w"] == 1 and d["cxp"] == 1 and d["n"] >= 3:
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
            await new Promise(r=>setTimeout(r,700));
            const bs=Array.from(document.querySelectorAll('button'));
            const btn=bs.find(x=>/\\u767b\\u5f55/.test(x.innerText))||bs[0];
            if(btn)btn.click(); }""", {"u": LOGIN, "p": PASSWD})

        tok = ""
        for i in range(45):
            await pg.wait_for_timeout(1000)
            try:
                tok = await pg.evaluate("() => localStorage.getItem('merchant-token')||''")
                if tok:
                    print(f"[+] login ok ~{i+1}s")
                    break
            except Exception:
                pass
        if not tok:
            print("[!] login failed"); await b.close(); return

        await pg.wait_for_timeout(3000)
        print("[url]", await pg.evaluate("() => location.href"))

        out = {}
        # Issue requests by re-using the app's own axios (interceptors add X-Ch/X-Ck/X-Ws)
        for path, body in POSTS:
            r = await pg.evaluate("""async (a) => {
                const ax = (window.__APP_AXIOS__) ||
                  (document.querySelector('#app') && document.querySelector('#app').__vue_app__
                    && document.querySelector('#app').__vue_app__.config.globalProperties.$http);
                if (!ax) return { s: -2, t: 'no-axios' };
                try { const z = await ax.post(a.u, a.b);
                      return { s: z.status, t: JSON.stringify(z.data).slice(0, 6000) }; }
                catch (e) { return { s: e.response ? e.response.status : -1,
                                     t: JSON.stringify(e.response ? e.response.data : String(e)).slice(0, 6000) }; } }""",
                                    {"u": path, "b": body})
            out["POST " + path] = r
            print(f"  POST {path:46s} st={r['s']:>4} {r['t'][:170]}")

        for path in GETS:
            r = await pg.evaluate("""async (u) => {
                const ax = (document.querySelector('#app') && document.querySelector('#app').__vue_app__
                    && document.querySelector('#app').__vue_app__.config.globalProperties.$http);
                if (!ax) return { s: -2, t: 'no-axios' };
                try { const z = await ax.get(u);
                      return { s: z.status, t: JSON.stringify(z.data).slice(0, 6000) }; }
                catch (e) { return { s: e.response ? e.response.status : -1,
                                     t: JSON.stringify(e.response ? e.response.data : String(e)).slice(0, 6000) }; } }""", path)
            out["GET " + path] = r
            print(f"  GET  {path:46s} st={r['s']:>4} {r['t'][:170]}")

        open(os.path.join(OUT, "fund_raw.json"), "w", encoding="utf-8").write(
            json.dumps(out, ensure_ascii=False, indent=1))
        print("\n[+] fund_raw.json saved")
        await b.close()


asyncio.run(main())
