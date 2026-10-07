import asyncio, json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.async_api import async_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TARGET = "https://merchant.lamuzhifu.top"
OUT = r"E:\IOSusdt"
PROXY = "http://127.0.0.1:10809"
LOGIN, PASSWD = "\u51a0\u519b", "<REDACTED_PASSWORD>"

# Record what the page itself fetches, and let the app's own interceptors run.
INIT = r"""
window.__NET = [];
window.__ENV = [];
window.__PLAIN = [];
(function () {
  const oParse = JSON.parse;
  window.JSON.parse = function (t, r) {
    const v = oParse.call(this, t, r);
    try {
      if (v && typeof v === 'object' && !Array.isArray(v)) {
        if (v.v === 3 && typeof v.p === 'string' && typeof v.q === 'string') {
          window.__ENV.push(v);
        } else { window.__PLAIN.push(v); }
      }
    } catch (e) {}
    return v;
  };
  const of = window.fetch;
  window.fetch = function (i, n) {
    const rec = { url: String(i && i.url ? i.url : i), m: (n && n.method) || 'GET',
                  body: n && typeof n.body === 'string' ? n.body.slice(0, 4000) : null,
                  headers: n && n.headers ? JSON.parse(JSON.stringify(n.headers)) : null,
                  status: null, resp: null };
    window.__NET.push(rec);
    return of.apply(this, arguments).then(function (r) {
      rec.status = r.status;
      try { r.clone().text().then(function (t) { rec.resp = t.slice(0, 20000); }); } catch (e) {}
      return r;
    });
  };
})();
"""

ROUTES = [
    "/dashboard",
    "/AgentManagement/AgentList",
    "/AgentManagement/AgentLoginManagement",
    "/AgentManagement/AgencyCommissionAudit",
    "/AgencyCommissionAudit",
    "/CommissionList",
    "/DailyReport",
    "/AccountManagement/LoginManagement",
    "/MerchantOrderList",
    "/fund/FundDetails",
    "/fund/RechargeRecord",
    "/Pay/payInOrderList",
    "/Pay/payOutOrderList",
    "/IP",
    "/ApiKeyManagement",
    "/Channels",
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
        await pg.wait_for_timeout(3000)

        seen = {}
        for route in ROUTES:
            await pg.evaluate("() => { window.__NET=[]; window.__PLAIN=[]; window.__ENV=[]; }")
            try:
                await pg.goto(TARGET + route, wait_until="commit", timeout=35000)
                await pg.wait_for_timeout(6500)
            except Exception as e:
                print(f"{route:44s} nav-warn")
                continue
            net = json.loads(await pg.evaluate("() => JSON.stringify(window.__NET||[])"))
            plain = json.loads(await pg.evaluate("() => JSON.stringify(window.__PLAIN||[])"))
            txt = await pg.evaluate("() => (document.body.innerText||'').replace(/\\s+/g,' ').slice(0,700)")
            print(f"\n{'='*76}\n{route}")
            print("-"*76)
            print("TEXT:", txt[:500])
            for r_ in net:
                if "/api/" not in str(r_["url"]):
                    continue
                u = str(r_["url"]).split("?")[0]
                seen.setdefault(u, []).append({"route": route, "status": r_["status"],
                                               "body": r_.get("body"), "resp": r_.get("resp")})
                print(f"   {r_['m']:5s} {u:46s} st={r_['status']} r={len(r_.get('resp') or '')}")
            if plain:
                for pl in plain[:6]:
                    s_ = json.dumps(pl, ensure_ascii=False)
                    if len(s_) > 40:
                        print("   PLAIN:", s_[:400])

        open(os.path.join(OUT, "agent_probe.json"), "w", encoding="utf-8").write(
            json.dumps(seen, ensure_ascii=False, indent=1))
        print("\n[+] agent_probe.json saved")
        await b.close()


asyncio.run(main())
