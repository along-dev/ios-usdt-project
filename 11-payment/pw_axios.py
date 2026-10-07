import asyncio, json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.async_api import async_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TARGET = "https://merchant.lamuzhifu.top"
OUT = r"E:\IOSusdt"
INIT = open(os.path.join(OUT, "pw_init_env.js"), encoding="utf-8").read()
PROXY = "http://127.0.0.1:10809"
LOGIN, PASSWD = "\u51a0\u519b", "<REDACTED_PASSWORD>"


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
        await pg.wait_for_timeout(6000)

        # Which globals does the bundle expose?
        g = await pg.evaluate(r"""() => {
            const names = ['encrypt','decrypt','azhifuRsaDecrypt','azhifuRsaWrapGetKey',
                           'azhifuRsaEncryptPost','azhifuRsaShouldEncryptGet','cxBox','cxReady',
                           'azhifuRsaPublicKey','azhifuRsaGetEncryptUrls'];
            const o = {};
            for (const n of names) o[n] = typeof window[n];
            o.__cxKeys = window.__cx ? Object.keys(window.__cx).join(',') : null;
            return o; }""")
        print("[globals]", json.dumps(g, ensure_ascii=False))

        # Envelopes observed by the JSON.parse hook
        envs = json.loads(await pg.evaluate(
            "() => JSON.stringify((window.__NET||[]).filter(x=>x.kind==='envelope').map(x=>x.env))"))
        print(f"\n[+] envelopes seen: {len(envs)}")

        # Force the app itself to fetch+decrypt a target endpoint, then read
        # the plaintext straight out of the axios response object.
        targets = [
            ("GET", "/api/Account/Self", None),
            ("GET", "/api/Home/Dashboard", None),
            ("GET", "/api/System/Settings", None),
            ("GET", "/api/ApiKey/List", None),
            ("GET", "/api/AuthorizedIp/List", None),
            ("POST", "/api/CommissionSettlement/List", {"Pager": {"PageIndex": 1, "PageSize": 20}, "Condition": {}}),
            ("POST", "/api/Transaction/List", {"Pager": {"PageIndex": 1, "PageSize": 20}, "Condition": {}}),
            ("POST", "/api/BalanceRecord/List", {"Pager": {"PageIndex": 1, "PageSize": 20}, "Condition": {}}),
            ("POST", "/api/MerchantOrder/List", {"Pager": {"PageIndex": 1, "PageSize": 20}, "Condition": {}}),
            ("POST", "/api/WebOrder/ApplyWithdrawalOrders", {"Pager": {"PageIndex": 1, "PageSize": 20}, "Condition": {}}),
            ("POST", "/api/Agent/Subordinates", {"Pager": {"PageIndex": 1, "PageSize": 20}, "Condition": {}}),
        ]
        results = {}
        for method, path, body in targets:
            r = await pg.evaluate(r"""async (a) => {
                // find the axios instance the SPA installed on its HTTP service
                const cands = [];
                if (window.axios) cands.push(window.axios);
                if (window.$http) cands.push(window.$http);
                if (window.http) cands.push(window.http);
                if (window.request) cands.push(window.request);
                // probe vue global properties
                const el = document.querySelector('#app');
                const app = el && el.__vue_app__;
                if (app) {
                  const gp = app.config && app.config.globalProperties;
                  if (gp) for (const k of Object.keys(gp)) {
                    const v = gp[k];
                    if (v && typeof v === 'object' && typeof v.get === 'function' && typeof v.post === 'function') {
                      cands.push(v);
                    }
                    if (v && typeof v.request === 'function') cands.push(v);
                  }
                }
                if (!cands.length) return { s: -2, t: 'no axios candidate' };
                const ax = cands[0];
                try {
                  const cfg = a.m === 'GET' ? { url: a.u, method: 'get' }
                                            : { url: a.u, method: 'post', data: a.b };
                  const z = await ax(cfg);
                  return { s: z.status, t: JSON.stringify(z.data).slice(0, 8000),
                           via: 'axios' };
                } catch (e) {
                  const rr = e && e.response;
                  return { s: rr ? rr.status : -1,
                           t: JSON.stringify(rr ? rr.data : String(e)).slice(0, 8000),
                           via: 'axios-err' };
                }
            }""", {"m": method, "u": path, "b": body})
            results[f"{method} {path}"] = r
            print(f"\n  {method:4s} {path:44s} st={r['s']:>4} via={r.get('via')}")
            print("       " + str(r["t"])[:600])

        open(os.path.join(OUT, "fund_plain.json"), "w", encoding="utf-8").write(
            json.dumps(results, ensure_ascii=False, indent=1))
        print("\n[+] fund_plain.json saved")
        await b.close()


asyncio.run(main())
