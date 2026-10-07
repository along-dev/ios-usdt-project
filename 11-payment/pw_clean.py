import asyncio, json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.async_api import async_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TARGET = "https://merchant.lamuzhifu.top"
OUT = r"E:\IOSusdt"
INIT = open(os.path.join(OUT, "pw_init_clean.js"), encoding="utf-8").read()
PROXY = "http://127.0.0.1:10809"

LOGIN = "\u51a0\u519b"
PASSWD = "<REDACTED_PASSWORD>"


async def run(p, label, proxy):
    print(f"\n{'='*68}\n[RUN] {label}  proxy={proxy}\n{'='*68}")
    kw = {"proxy": {"server": proxy}} if proxy else {}
    b = await p.chromium.launch(
        headless=True, executable_path=CHROME,
        args=["--ignore-certificate-errors", "--no-sandbox",
              "--disable-blink-features=AutomationControlled"], **kw)
    ctx = await b.new_context(ignore_https_errors=True,
                              viewport={"width": 1920, "height": 1080})
    await ctx.add_init_script(INIT)
    pg = await ctx.new_page()
    pg.on("pageerror", lambda e: None)
    await pg.goto(TARGET + "/login", wait_until="commit", timeout=60000)

    st = None
    for i in range(40):
        await pg.wait_for_timeout(1000)
        try:
            st = await pg.evaluate("""() => ({ w: window.__cx ? window.__cx.w : null,
                cxp: window.__cxp || null, wrid: sessionStorage.getItem('_wrid'),
                inputs: document.querySelectorAll('input').length,
                pubs: (window.__NET||[]).filter(x =>
                        String(x.url).indexOf('PublicSettings')>=0).length })""")
        except Exception:
            continue
        if st and st["w"] == 1 and st["cxp"] == 1 and st["pubs"] >= 1 and st["inputs"] >= 3:
            print(f"[ready ~{i+1}s]", json.dumps(st))
            break
    else:
        print("[!] not ready:", json.dumps(st))

    # Check the PublicSettings verdict BEFORE login
    verdict = await pg.evaluate("""() => {
        const r = (window.__NET||[]).find(x => String(x.url).indexOf('PublicSettings')>=0);
        return r ? { status: r.status, resp: (r.resp||'').slice(0,200) } : null; }""")
    print("[pre-login PublicSettings]", json.dumps(verdict, ensure_ascii=False))

    await pg.evaluate("""async (c) => {
        const set = (el, v) => { const d = Object.getOwnPropertyDescriptor(el.__proto__, 'value');
          d && d.set ? d.set.call(el, v) : (el.value = v);
          el.dispatchEvent(new Event('input',{bubbles:true}));
          el.dispatchEvent(new Event('change',{bubbles:true})); };
        const ins = Array.from(document.querySelectorAll('input'));
        const u = ins.find(i => i.name==='username' || i.type==='text');
        const pw = ins.find(i => i.name==='password' || i.type==='password');
        const tt = ins.find(i => i.name==='Totp');
        if (u) set(u, c.u); if (pw) set(pw, c.p); if (tt) set(tt, '');
        await new Promise(r => setTimeout(r, 700));
        const bs = Array.from(document.querySelectorAll('button'));
        const btn = bs.find(x => /\\u767b\\u5f55/.test(x.innerText)) || bs[0];
        if (btn) btn.click(); }""", {"u": LOGIN, "p": PASSWD})
    await pg.wait_for_timeout(10000)

    after = await pg.evaluate("""() => ({ url: location.href,
        ls: Object.keys(localStorage).join(','),
        mt: (localStorage.getItem('merchant-token')||'').slice(0,30),
        at: (localStorage.getItem('admtoken')||'').slice(0,30) })""")
    recs = json.loads(await pg.evaluate("() => JSON.stringify(window.__NET||[])"))
    print(f"[after] url={after['url']}  ls=[{after['ls']}]  mt={after['mt'][:18] or '-'}")
    for r_ in recs:
        try:
            m = json.loads(r_.get("resp") or "{}")
            msg = f"Code={m.get('Code')} {m.get('Message','')}" if isinstance(m, dict) else ""
        except Exception:
            msg = "(binary/envelope)"
        print(f"   {r_['method']:5s} {str(r_['url'])[:50]:50s} st={r_['status']} "
              f"r={len(r_.get('resp') or '')} {msg}")
    open(os.path.join(OUT, f"pw_net_{label}.json"), "w", encoding="utf-8").write(
        json.dumps(recs, ensure_ascii=False, indent=1))
    await pg.screenshot(path=os.path.join(OUT, f"pw_{label}.png"), full_page=True)
    await b.close()
    return recs


async def main():
    async with async_playwright() as p:
        await run(p, "clean_proxy", PROXY)


asyncio.run(main())
