import asyncio, json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.async_api import async_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TARGET = "https://merchant.lamuzhifu.top"
OUT = r"E:\IOSusdt"
INIT = open(os.path.join(OUT, "pw_init_plain.js"), encoding="utf-8").read()
PROXY = "http://127.0.0.1:10809"
LOGIN, PASSWD = "\u51a0\u519b", "<REDACTED_PASSWORD>"


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


FIND_DECRYPT = r"""
() => {
  const out = { found: false, how: null, keys: [] };
  // 1) webpack 5 runtime
  const chunkKeys = Object.keys(window).filter(k => /^webpackChunk/.test(k));
  out.chunkKeys = chunkKeys;
  const probe = (arr) => {
    let req = null;
    try {
      arr.push([[Symbol('probe')], {}, (r) => { req = r; }]);
    } catch (e) { return null; }
    return req;
  };
  for (const ck of chunkKeys) {
    const arr = window[ck];
    if (!arr || !arr.push) continue;
    const req = probe(arr);
    if (!req || !req.m) continue;
    out.how = ck;
    const hits = [];
    for (const id of Object.keys(req.m)) {
      let mod = null;
      try { mod = req(id); } catch (e) { continue; }
      if (!mod || typeof mod !== 'object') continue;
      for (const k of Object.keys(mod)) {
        if (typeof mod[k] === 'function' &&
            ['encrypt','decrypt','azhifuRsaWrapGetKey','azhifuRsaDecrypt',
             'azhifuRsaEncryptPost','cxReady'].indexOf(k) >= 0) {
          hits.push({ id: id, name: k });
        }
      }
    }
    out.keys = hits;
    if (hits.length) { out.found = true; break; }
  }
  return out;
}
"""


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
        await pg.wait_for_timeout(6000)

        res = await pg.evaluate(FIND_DECRYPT)
        print("[webpack scan]", json.dumps(res, ensure_ascii=False, indent=2)[:2000])

        # also look for the interceptors on the axios instance the app uses
        axinfo = await pg.evaluate(r"""
        () => {
          const out = {};
          // Vue 3 app instance
          const el = document.querySelector('#app');
          const app = el && el.__vue_app__;
          out.hasVueApp = !!app;
          if (app) {
            out.gp = app.config && app.config.globalProperties
                       ? Object.keys(app.config.globalProperties).slice(0, 60) : null;
          }
          // global axios
          out.windowAxios = typeof window.axios;
          if (window.axios) {
            out.reqInt = window.axios.interceptors.request.handlers.length;
            out.resInt = window.axios.interceptors.response.handlers.length;
          }
          out.vueProto = typeof window.Vue;
          return out;
        }""")
        print("\n[axios/vue]", json.dumps(axinfo, ensure_ascii=False))

        # direct: pull the module cache and call decrypt on a captured ciphertext
        got = await pg.evaluate(r"""
        () => {
          const chunkKeys = Object.keys(window).filter(k => /^webpackChunk/.test(k));
          const found = {};
          for (const ck of chunkKeys) {
            const arr = window[ck];
            if (!arr || !arr.push) continue;
            let req = null;
            try { arr.push([[Symbol('p2')], {}, (r) => { req = r; }]); } catch (e) { continue; }
            if (!req || !req.m) continue;
            for (const id of Object.keys(req.m)) {
              let mod = null;
              try { mod = req(id); } catch (e) { continue; }
              if (!mod) continue;
              for (const k of Object.keys(mod)) {
                if (typeof mod[k] === 'function' &&
                    /^(encrypt|decrypt)$/.test(k)) {
                  found[k] = { id: id, src: String(mod[k]).slice(0, 600) };
                }
              }
            }
          }
          return found;
        }""")
        print("\n[decrypt/encrypt sources]", json.dumps(got, ensure_ascii=False, indent=2)[:3000])
        await b.close()


asyncio.run(main())
