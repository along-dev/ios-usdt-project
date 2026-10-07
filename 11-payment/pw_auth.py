import asyncio, json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.async_api import async_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TARGET = "https://merchant.lamuzhifu.top"
OUT = r"E:\IOSusdt"
INIT = open(os.path.join(OUT, "pw_init_clean.js"), encoding="utf-8").read()
PROXY = "http://127.0.0.1:10809"
LOGIN, PASSWD = "\u51a0\u519b", "<REDACTED_PASSWORD>"


async def login(pg, log):
    """Fill the real form and click 登录. Returns True when a token appears."""
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
        try:
            t = await pg.evaluate("() => localStorage.getItem('merchant-token') || ''")
            if t:
                log(f"[+] LOGIN OK ~{i+1}s token_len={len(t)}")
                return t
        except Exception:
            pass
    return ""


async def attempt(p, label, ctx_kw, launch_args, headless=False):
    print(f"\n{'='*66}\n[ATTEMPT] {label}\n{'='*66}")
    b = await p.chromium.launch(headless=headless, executable_path=CHROME,
                                proxy={"server": PROXY},
                                args=["--ignore-certificate-errors", "--no-sandbox",
                                      "--disable-blink-features=AutomationControlled"] + launch_args)
    ctx = await b.new_context(ignore_https_errors=True, **ctx_kw)
    await ctx.add_init_script(INIT)
    pg = await ctx.new_page()
    await pg.goto(TARGET + "/login", wait_until="commit", timeout=60000)
    for i in range(40):
        await pg.wait_for_timeout(1000)
        try:
            d = await pg.evaluate("""() => ({ w: window.__cx?window.__cx.w:null,
                cxp: window.__cxp||null, n: document.querySelectorAll('input').length,
                ow: window.outerWidth, oh: window.outerHeight })""")
        except Exception:
            continue
        if d and d["w"] == 1 and d["cxp"] == 1 and d["n"] >= 3:
            print(f"[ready ~{i+1}s] {json.dumps(d)}")
            break
    await pg.wait_for_timeout(2000)
    tok = await login(pg, print)
    if tok:
        info = await pg.evaluate("""() => ({ url: location.href,
            keys: Object.keys(localStorage).join(','),
            ui: (localStorage.getItem('userInfo')||'').slice(0,400) })""")
        print("[state]", json.dumps(info, ensure_ascii=False)[:500])
        await pg.screenshot(path=os.path.join(OUT, f"pw_ok_{label}.png"), full_page=True)
        await b.close()
        return tok, info
    print("[!] login failed; url=", await pg.evaluate("() => location.href"))
    await pg.screenshot(path=os.path.join(OUT, f"pw_fail_{label}.png"), full_page=True)
    await b.close()
    return "", {}


async def main():
    async with async_playwright() as p:
        # exact replica of the config that already succeeded
        tok, info = await attempt(
            p, "replica",
            dict(viewport={"width": 1920, "height": 1080},
                 screen={"width": 1920, "height": 1080}),
            ["--window-size=1920,1080"])
        if tok:
            open(os.path.join(OUT, "token.json"), "w", encoding="utf-8").write(
                json.dumps({"token": tok, **info}, ensure_ascii=False, indent=1))
            print("\n[+] token.json written")
            return
        # fallback: no explicit viewport, let the window decide
        tok, info = await attempt(p, "no_viewport", {}, ["--window-size=1600,900"])
        if tok:
            open(os.path.join(OUT, "token.json"), "w", encoding="utf-8").write(
                json.dumps({"token": tok, **info}, ensure_ascii=False, indent=1))
            print("\n[+] token.json written")


asyncio.run(main())
