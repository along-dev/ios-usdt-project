import asyncio, json, os, sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.async_api import async_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TARGET = "https://merchant.lamuzhifu.top"
OUT = r"E:\IOSusdt"
PROXY = "http://127.0.0.1:10809"
LOGIN, PASSWD = "\u51a0\u519b", "<REDACTED_PASSWORD>"

INIT = r"""
window.__NET = [];
window.__SRC = [];
(function () {
  const of = window.fetch;
  window.fetch = function (i, n) {
    window.__NET.push({ url: String(i && i.url ? i.url : i), m: (n && n.method) || 'GET' });
    return of.apply(this, arguments);
  };
  // record dynamically inserted scripts
  const obs = new MutationObserver(ms => {
    for (const m of ms) for (const n of m.addedNodes) {
      if (n.tagName === 'SCRIPT' && n.src) window.__SRC.push(n.src);
      if (n.tagName === 'LINK' && n.href) window.__SRC.push(n.href);
    }
  });
  obs.observe(document.documentElement, { childList: true, subtree: true });
})();
"""

ROUTES = ["/dashboard", "/AgentManagement/AgentList", "/AgentManagement/AgentLoginManagement",
          "/AgentManagement/AgencyCommissionAudit", "/AgencyCommissionAudit",
          "/AccountManagement/LoginManagement", "/CommissionList", "/DailyReport"]


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

        # collect all script srcs the app loaded, across routes
        seen = set()
        for route in ROUTES:
            try:
                await pg.goto(TARGET + route, wait_until="commit", timeout=35000)
                await pg.wait_for_timeout(5000)
            except Exception:
                continue
            srcs = await pg.evaluate("""() => Array.from(document.querySelectorAll('script[src]'))
                                        .map(s => s.src)""")
            seen |= set(srcs)
            api = json.loads(await pg.evaluate("() => JSON.stringify((window.__NET||[]))"))
            print(f"  {route:44s} scripts={len(srcs)} api={len(api)}")

        print(f"\n[*] unique scripts: {len(seen)}")
        for s_ in sorted(seen):
            print("   ", s_)

        # also: what does the app route table contain for roles?
        routes = await pg.evaluate(r"""() => {
            const el = document.querySelector('#app');
            const app = el && el.__vue_app__;
            return { hasApp: !!app, sysMode: (window.localStorage.getItem('userInfo')||'') }; }""")
        print("\n[app]", json.dumps(routes, ensure_ascii=False))
        await b.close()


asyncio.run(main())
