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
(function () {
  const oParse = JSON.parse;
  window.JSON.parse = function (t, r) {
    const v = oParse.call(this, t, r);
    try {
      if (v && typeof v === 'object' && !Array.isArray(v)
          && !(v.v === 3 && v.p && v.q)) { window.__PLAIN.push(v); }
    } catch (e) {}
    return v;
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
        await pg.wait_for_timeout(5000)

        plain = json.loads(await pg.evaluate("() => JSON.stringify(window.__PLAIN||[])"))

        # extract and pretty-print ALL system settings
        for obj in plain:
            data = obj.get("Data")
            if isinstance(data, list) and data and isinstance(data[0], dict) and "Key" in data[0]:
                print("=" * 78)
                print("FULL SYSTEM SETTINGS  (%d entries)" % len(data))
                print("=" * 78)
                for it in data:
                    k = it.get("Key"); v = it.get("Value"); t = it.get("Title") or ""
                    print(f"  {k:46s} = {str(v)[:90]:90s} {t}")
                json.dump(data, open(os.path.join(OUT, "sys_settings.json"), "w",
                                     encoding="utf-8"), ensure_ascii=False, indent=1)

        print("\n" + "=" * 78)
        print("ALL DECRYPTED PAYLOADS")
        print("=" * 78)
        for i, obj in enumerate(plain):
            s_ = json.dumps(obj, ensure_ascii=False)
            if len(s_) < 30:
                continue
            print(f"\n[{i}] {s_[:1200]}")
        json.dump(plain, open(os.path.join(OUT, "all_plain.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("\n[+] sys_settings.json + all_plain.json saved")
        await b.close()


asyncio.run(main())
