import asyncio, json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.async_api import async_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TARGET = "https://merchant.lamuzhifu.top"
OUT = r"E:\IOSusdt"
INIT = open(os.path.join(OUT, "pw_init_clean.js"), encoding="utf-8").read()
PROXY = "http://127.0.0.1:10809"
LOGIN, PASSWD = "\u51a0\u519b", "<REDACTED_PASSWORD>"

# Every frontend route discovered in app_bundle.js
ROUTES = [
    "/dashboard",
    "/fund/FundDetails",
    "/fund/RechargeRecord",
    "/Pay/payInOrderList",
    "/Pay/payOutOrderList",
    "/MerchantOrderList",
    "/CommissionList",
    "/DailyReport",
    "/AgentList",
    "/AgencyCommissionAudit",
    "/AgentLoginManagement",
    "/ApiKeyManagement",
    "/IP",
    "/Channels",
    "/LoginManagement",
    "/batchPayment",
    "/DocumentCenter",
    "/AccountManagement",
    "/AgentManagement",
]


async def do_login(pg, log=print):
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
    for i in range(45):
        await pg.wait_for_timeout(1000)
        t = await pg.evaluate("() => localStorage.getItem('merchant-token')||''")
        if t:
            log(f"[+] login ok ~{i+1}s")
            return t
    return ""


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

        tok = await do_login(pg)
        if not tok:
            print("[!] login failed"); await b.close(); return
        await pg.wait_for_timeout(3000)

        # reset the network log, then walk routes so the SPA itself calls its APIs
        await pg.evaluate("() => { window.__NET.length = 0; }")

        report = {}
        for route in ROUTES:
            try:
                await pg.goto(TARGET + route, wait_until="commit", timeout=40000)
            except Exception as e:
                print(f"  {route:34s} nav-warn {str(e)[:40]}")
                continue
            await pg.wait_for_timeout(7000)   # let the page finish its initial load
            url = await pg.evaluate("() => location.pathname")
            recs = json.loads(await pg.evaluate(
                "() => JSON.stringify((window.__NET||[]).filter(x => String(x.url).indexOf('/api/')>=0))"))
            apis = {}
            for r_ in recs:
                u = str(r_["url"]).split("?")[0]
                if u not in apis:
                    apis[u] = {"status": r_["status"], "resp": r_.get("resp") or "",
                               "body": r_.get("body") or "", "method": r_["method"]}
            ok = [u for u, v in apis.items() if v["status"] == 200 and len(v["resp"]) > 80]
            print(f"  {route:34s} -> {url:34s} api={len(apis):3d} usable={len(ok):3d}")
            report[route] = {"url": url, "apis": apis}
            await pg.evaluate("() => { window.__NET.length = 0; }")

        open(os.path.join(OUT, "fund_routes.json"), "w", encoding="utf-8").write(
            json.dumps(report, ensure_ascii=False, indent=1))
        print("\n[+] fund_routes.json saved")

        # summary of every endpoint carrying real payloads
        print("\n" + "=" * 78)
        print("ENDPOINTS RETURNING DATA")
        print("=" * 78)
        seen = {}
        for route, info in report.items():
            for u, v in info["apis"].items():
                if v["status"] == 200 and len(v["resp"]) > 80:
                    seen.setdefault((v["method"], u), (route, v))
        for (m, u), (route, v) in sorted(seen.items()):
            print(f"\n--- {m} {u}   (via {route}) len={len(v['resp'])}")
            print("    " + v["resp"][:700])
        await pg.screenshot(path=os.path.join(OUT, "pw_last.png"), full_page=True)
        await b.close()


asyncio.run(main())
