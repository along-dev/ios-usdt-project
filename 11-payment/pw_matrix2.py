import asyncio, json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.async_api import async_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TARGET = "https://merchant.lamuzhifu.top"
OUT = r"E:\IOSusdt"
PROXY = "http://127.0.0.1:10809"
LOGIN, PASSWD = "\u51a0\u519b", "<REDACTED_PASSWORD>"

# Observe what the app itself asks for, keyed by endpoint.
INIT = r"""
window.__REQ = [];
window.__PLAIN = [];
(function () {
  const oParse = JSON.parse;
  window.JSON.parse = function (t, r) {
    const v = oParse.call(this, t, r);
    try {
      if (v && typeof v === 'object' && !Array.isArray(v) && !(v.v === 3 && v.p && v.q))
        window.__PLAIN.push(v);
    } catch (e) {}
    return v;
  };
  const ox = XMLHttpRequest.prototype.open;
  const os_ = XMLHttpRequest.prototype.send;
  const oh = XMLHttpRequest.prototype.setRequestHeader;
  XMLHttpRequest.prototype.open = function (m, u) {
    this.__p = { m: m, u: u, h: {} }; return ox.apply(this, arguments);
  };
  XMLHttpRequest.prototype.setRequestHeader = function (k, v) {
    if (this.__p) this.__p.h[k] = v; return oh.apply(this, arguments);
  };
  XMLHttpRequest.prototype.send = function (b) {
    if (this.__p) {
      this.__p.body = typeof b === 'string' ? b.slice(0, 2000) : null;
      const s = this;
      this.addEventListener('load', function () {
        s.__p.st = s.status;
        const t = String(s.responseText);
        s.__p.raw = t.slice(0, 300);
        try { const j = oParse(t);
              s.__p.plain = JSON.stringify(j).slice(0, 900); } catch (e) {}
      });
      window.__REQ.push(this.__p);
    }
    return os_.apply(this, arguments);
  };
  const of = window.fetch;
  window.fetch = function (i, n) {
    const rec = { m: (n && n.method) || 'GET', u: String(i && i.url ? i.url : i),
                  h: (n && n.headers) ? JSON.parse(JSON.stringify(n.headers)) : {},
                  body: n && typeof n.body === 'string' ? n.body.slice(0, 2000) : null };
    window.__REQ.push(rec);
    return of.apply(this, arguments).then(function (r) {
      rec.st = r.status;
      try { r.clone().text().then(function (t) {
        rec.raw = t.slice(0, 300);
        try { const j = oParse(t); rec.plain = JSON.stringify(j).slice(0, 900); } catch (e) {}
      }); } catch (e) {}
      return r;
    });
  };
})();
"""


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


ROUTES = [
    "/dashboard",
    "/MerchantOrderList",
    "/Pay/payInOrderList",
    "/Pay/payOutOrderList",
    "/fund/FundDetails",
    "/fund/RechargeRecord",
    "/CommissionList",
    "/DailyReport",
    "/AgentManagement/AgentList",
    "/AgentManagement/AgencyCommissionAudit",
    "/AccountManagement/LoginManagement",
    "/ApiKeyManagement",
    "/IP",
    "/Channels",
    "/batchPayment",
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
        tok = await do_login(pg)
        if not tok:
            print("[!] login failed"); await b.close(); return
        await pg.wait_for_timeout(3000)

        agg = {}
        for route in ROUTES:
            await pg.evaluate("() => { window.__REQ=[]; window.__PLAIN=[]; }")
            try:
                await pg.goto(TARGET + route, wait_until="commit", timeout=35000)
                await pg.wait_for_timeout(6500)
            except Exception:
                print(f"{route:44s} nav-warn"); continue
            reqs = json.loads(await pg.evaluate("() => JSON.stringify(window.__REQ||[])"))
            plain = json.loads(await pg.evaluate("() => JSON.stringify(window.__PLAIN||[])"))
            api = [r_ for r_ in reqs if "/api/" in str(r_.get("u", ""))]
            print(f"\n{route:44s} api={len(api)}")
            for r_ in api:
                u = str(r_["u"]).split("?")[0]
                pl = r_.get("plain") or r_.get("raw") or ""
                agg.setdefault(u, {"m": r_["m"], "st": r_.get("st"), "plain": pl,
                                   "routes": []})["routes"].append(route)
                print(f"    {r_['m']:5s} {u:44s} st={r_.get('st')} {pl[:130]}")
            for pl in plain[:8]:
                s_ = json.dumps(pl, ensure_ascii=False)
                if len(s_) > 60:
                    print("    PLAIN:", s_[:260])

        json.dump(agg, open(os.path.join(OUT, "route_matrix.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("\n" + "=" * 90)
        print("ENDPOINT MATRIX")
        print("=" * 90)
        for u, v in sorted(agg.items()):
            print(f"  {v['m']:5s} {u:46s} st={v['st']}  via {','.join(sorted(set(v['routes'])))[:60]}")
        print("\n[+] route_matrix.json saved")
        await b.close()


asyncio.run(main())
