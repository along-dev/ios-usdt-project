import asyncio, json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.async_api import async_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TARGET = "https://merchant.lamuzhifu.top"
OUT = r"E:\IOSusdt"
INIT = open(os.path.join(OUT, "pw_init_map.js"), encoding="utf-8").read()
PROXY = "http://127.0.0.1:10809"
LOGIN, PASSWD = "\u51a0\u519b", "<REDACTED_PASSWORD>"

ROUTES = [
    "/dashboard",
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
    "/LoginManagement",
]


async def do_login(pg):
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
            print(f"[+] login ok ~{i+1}s")
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
        await pg.wait_for_timeout(4000)

        summary = {}
        for route in ROUTES:
            try:
                await pg.goto(TARGET + route, wait_until="commit", timeout=40000)
            except Exception as e:
                print(f"{route:32s} nav-warn {str(e)[:40]}")
                continue
            await pg.wait_for_timeout(7000)

            info = await pg.evaluate(r"""() => {
                const txt = (document.body.innerText || '').replace(/\n{3,}/g, '\n\n');
                const tables = Array.from(document.querySelectorAll('table')).map(t =>
                    (t.innerText || '').slice(0, 3000));
                const cards = Array.from(document.querySelectorAll(
                    '.el-card, .ant-card, .card, [class*=statistic], [class*=overview]'
                )).slice(0, 20).map(c => (c.innerText || '').replace(/\s+/g, ' ').slice(0, 400));
                return { path: location.pathname, title: document.title,
                         text: txt.slice(0, 6000), tables: tables, cards: cards,
                         plain: (window.__PLAIN || []).slice(-40),
                         envCount: (window.__ENV || []).length };
            }""")
            summary[route] = info
            print(f"\n{'='*76}\n{route}  -> {info['path']}   envelopes={info['envCount']}")
            print("-" * 76)
            print(info["text"][:1800])
            if info["tables"]:
                for i, t in enumerate(info["tables"][:3]):
                    print(f"  [table {i}] {t[:500]}")
            await pg.evaluate("() => { window.__PLAIN = []; window.__ENV = []; }")

        open(os.path.join(OUT, "pages_dump.json"), "w", encoding="utf-8").write(
            json.dumps(summary, ensure_ascii=False, indent=1))
        print("\n[+] pages_dump.json saved")
        await b.close()


asyncio.run(main())
