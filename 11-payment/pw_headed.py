import asyncio, json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.async_api import async_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TARGET = "https://merchant.lamuzhifu.top"
OUT = r"E:\IOSusdt"
INIT = open(os.path.join(OUT, "pw_init_clean.js"), encoding="utf-8").read()
PROXY = "http://127.0.0.1:10809"
LOGIN, PASSWD = "\u51a0\u519b", "<REDACTED_PASSWORD>"


async def run(p, label, headless, extra_args, proxy=PROXY):
    print(f"\n{'='*68}\n[RUN] {label} headless={headless}\n{'='*68}")
    kw = {"proxy": {"server": proxy}} if proxy else {}
    b = await p.chromium.launch(headless=headless, executable_path=CHROME,
                                args=["--ignore-certificate-errors", "--no-sandbox",
                                      "--disable-blink-features=AutomationControlled",
                                      "--window-size=1920,1080"] + extra_args, **kw)
    ctx = await b.new_context(ignore_https_errors=True,
                              viewport={"width": 1920, "height": 1080},
                              screen={"width": 1920, "height": 1080})
    await ctx.add_init_script(INIT)
    pg = await ctx.new_page()
    await pg.goto(TARGET + "/login", wait_until="commit", timeout=60000)

    dims = None
    for i in range(40):
        await pg.wait_for_timeout(1000)
        try:
            dims = await pg.evaluate("""() => ({
                ow: window.outerWidth, iw: window.innerWidth,
                oh: window.outerHeight, ih: window.innerHeight,
                w: window.__cx ? window.__cx.w : null, cxp: window.__cxp || null,
                inputs: document.querySelectorAll('input').length,
                pubs: (window.__NET||[]).filter(x => String(x.url).indexOf('PublicSettings')>=0).length })""")
        except Exception:
            continue
        if dims and dims["w"] == 1 and dims["cxp"] == 1 and dims["pubs"] >= 1 and dims["inputs"] >= 3:
            print(f"[ready ~{i+1}s]", json.dumps(dims))
            break
    else:
        print("[!] not ready:", json.dumps(dims))

    v = await pg.evaluate("""() => { const r=(window.__NET||[]).find(x=>
        String(x.url).indexOf('PublicSettings')>=0);
        return r? { status:r.status, ck:(r.headers&&(r.headers['X-Ck']||r.headers['x-ck'])||'').length,
                    resp:(r.resp||'').slice(0,150) } : null; }""")
    print("[pre-login PublicSettings]", json.dumps(v, ensure_ascii=False))

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
    await pg.wait_for_timeout(10000)

    after = await pg.evaluate("""() => ({ url: location.href,
        ls: Object.keys(localStorage).join(','),
        mt: (localStorage.getItem('merchant-token')||'').slice(0,24),
        at: (localStorage.getItem('admtoken')||'').slice(0,24),
        sk: (localStorage.getItem('supplier-token')||'').slice(0,24) })""")
    recs = json.loads(await pg.evaluate("() => JSON.stringify(window.__NET||[])"))
    print(f"[after] url={after['url']} ls=[{after['ls']}]")
    print(f"        merchant-token={after['mt'][:20] or '-'}  admtoken={after['at'][:20] or '-'}")
    for r_ in recs:
        try:
            m = json.loads(r_.get("resp") or "{}")
            msg = f"Code={m.get('Code')} {m.get('Message','')}" if isinstance(m, dict) else ""
        except Exception:
            msg = "(envelope)"
        ck = (r_.get("headers") or {}).get("X-Ck", "")
        print(f"   {r_['method']:5s} {str(r_['url'])[:44]:44s} st={r_['status']} "
              f"r={len(r_.get('resp') or '')} ck={len(ck)} {msg}")
    open(os.path.join(OUT, f"pw_net_{label}.json"), "w", encoding="utf-8").write(
        json.dumps(recs, ensure_ascii=False, indent=1))
    await pg.screenshot(path=os.path.join(OUT, f"pw_{label}.png"), full_page=True)
    await b.close()
    return recs


async def main():
    async with async_playwright() as p:
        await run(p, "headed", False, [])


asyncio.run(main())
