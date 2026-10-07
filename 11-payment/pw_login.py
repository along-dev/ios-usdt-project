import asyncio, json, sys, os

from playwright.async_api import async_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TARGET = "https://merchant.lamuzhifu.top"
OUT = r"E:\IOSusdt"

LOGIN_NAME = "\u51a0\u519b"          # 冠军
PASSWORD = "<REDACTED_PASSWORD>"
TOTP = ""

INIT = r"""
(() => {
  const noop = function () {};
  const rawEval = window.eval;
  window.eval = function (src) {
    if (typeof src === 'string' && src.indexOf('debugger') !== -1) return undefined;
    return rawEval.call(window, src);
  };
  const RawFunction = window.Function;
  window.Function = new Proxy(RawFunction, {
    apply(t, a, args) {
      if (args.length && typeof args[args.length-1] === 'string'
          && args[args.length-1].indexOf('debugger') !== -1) return noop;
      return Reflect.apply(t, a, args);
    },
    construct(t, args) {
      if (args.length && typeof args[args.length-1] === 'string'
          && args[args.length-1].indexOf('debugger') !== -1) return noop;
      return Reflect.construct(t, args);
    }
  });
  window.__NET = [];
  const of = window.fetch;
  window.fetch = function (input, init) {
    const rec = { kind:'fetch', url:String(input && input.url ? input.url : input),
                  method:(init&&init.method)||'GET', headers:null, body:null, resp:null };
    try { rec.headers = init && init.headers ? JSON.parse(JSON.stringify(init.headers)) : null;
          rec.body = init && typeof init.body === 'string' ? init.body.slice(0,20000) : null; } catch(e){}
    window.__NET.push(rec);
    return of.apply(this, arguments).then(async r => {
      try { rec.resp = (await r.clone().text()).slice(0, 20000); } catch(e){}
      return r;
    });
  };
  const oo = XMLHttpRequest.prototype.open, os_ = XMLHttpRequest.prototype.send,
        oh = XMLHttpRequest.prototype.setRequestHeader;
  XMLHttpRequest.prototype.open = function (m,u){ this.__p={kind:'xhr',method:m,url:u,headers:{}}; return oo.apply(this,arguments); };
  XMLHttpRequest.prototype.setRequestHeader = function (k,v){ if(this.__p) this.__p.headers[k]=v; return oh.apply(this,arguments); };
  XMLHttpRequest.prototype.send = function (b){
    if (this.__p){ this.__p.body = typeof b==='string'? b.slice(0,20000):null;
                   const self=this; this.addEventListener('load',function(){
                     try{ self.__p.resp = String(self.responseText).slice(0,20000);}catch(e){}
                   }); window.__NET.push(this.__p); }
    return os_.apply(this,arguments);
  };
})();
"""


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(
            headless=True, executable_path=CHROME,
            proxy={"server": "http://127.0.0.1:10809"},
            args=["--ignore-certificate-errors", "--no-sandbox",
                  "--disable-blink-features=AutomationControlled"],
        )
        ctx = await b.new_context(ignore_https_errors=True, viewport={"width": 1920, "height": 1080})
        await ctx.add_init_script(INIT)
        pg = await ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)[:200]))

        try:
            await pg.goto(TARGET + "/login", wait_until="commit", timeout=60000)
        except Exception as e:
            print("[!] goto:", str(e)[:100])
        await pg.wait_for_timeout(12000)

        # expose the app's own encrypt/decrypt from the webpack bundle
        have = await pg.evaluate("""() => ({
            cx: typeof window.__cx, w: window.__cx && window.__cx.w,
            cxp: window.__cxp, wrid: sessionStorage.getItem('_wrid'),
            enc: typeof window.encrypt, dec: typeof window.decrypt })""")
        print("[state]", json.dumps(have))

        # --- perform login by filling the real form and clicking the button ---
        filled = await pg.evaluate("""(creds) => {
            const set = (el, v) => {
              if (!el) return false;
              const d = Object.getOwnPropertyDescriptor(el.__proto__, 'value');
              d && d.set ? d.set.call(el, v) : (el.value = v);
              el.dispatchEvent(new Event('input', {bubbles:true}));
              el.dispatchEvent(new Event('change', {bubbles:true}));
              return true;
            };
            const ins = Array.from(document.querySelectorAll('input'));
            const u = ins.find(i => i.name === 'username' || i.type === 'text');
            const pw = ins.find(i => i.name === 'password' || i.type === 'password');
            const tt = ins.find(i => i.name === 'Totp');
            const a = set(u, creds.u); const bb = set(pw, creds.p);
            if (tt) set(tt, creds.t);
            return {user: a, pass: bb, totp: !!tt, n: ins.length};
        }""", {"u": LOGIN_NAME, "p": PASSWORD, "t": TOTP})
        print("[fill]", json.dumps(filled))
        await pg.wait_for_timeout(800)
        await pg.screenshot(path=os.path.join(OUT, "pw_01_filled.png"))

        # click 登录
        clicked = False
        try:
            await pg.get_by_role("button", name="\u767b\u5f55").first.click(timeout=8000)
            clicked = True
        except Exception as e:
            print("[!] role click failed:", str(e)[:120])
            try:
                await pg.evaluate("""() => {
                    const bs = Array.from(document.querySelectorAll('button'));
                    const b = bs.find(x => /\\u767b\\u5f55/.test(x.innerText));
                    if (b) b.click(); }""")
                clicked = True
            except Exception as e2:
                print("[!] js click failed:", str(e2)[:120])
        print("[click]", clicked)
        await pg.wait_for_timeout(9000)

        st = await pg.evaluate("""() => ({
            url: location.href, title: document.title,
            tok1: localStorage.getItem('merchant-token') ? 'YES' : 'no',
            tok2: localStorage.getItem('admtoken') ? 'YES' : 'no',
            keys: Object.keys(localStorage).join(','),
            cookie: document.cookie.slice(0, 200) })""")
        print("[after-login]", json.dumps(st, ensure_ascii=False))
        await pg.screenshot(path=os.path.join(OUT, "pw_02_after.png"))

        net = await pg.evaluate("""() => JSON.stringify((window.__NET||[]).map(x => ({
            m: x.method, u: String(x.url).slice(0, 90),
            h: Object.keys(x.headers||{}).join('|'),
            bl: (x.body||'').length,
            rl: (x.resp||'').length,
            rs: (x.resp||'').slice(0, 220) })))""")
        recs = json.loads(net)
        print(f"\n[net] {len(recs)} calls")
        for r_ in recs:
            print(f"  {r_['m']:5s} {r_['u']:60s} hdrs={r_['h'][:60]} b={r_['bl']} r={r_['rl']}")
        open(os.path.join(OUT, "pw_net.json"), "w", encoding="utf-8").write(
            json.dumps(recs, ensure_ascii=False, indent=1))
        print("\n[pageerrors]", errs[:3])
        await b.close()


asyncio.run(main())
