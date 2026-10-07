import asyncio, json, sys, os

from playwright.async_api import async_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TARGET = "https://merchant.lamuzhifu.top"
OUT = r"E:\IOSusdt"

# Neutralise anti-debug before any page script runs.
INIT = r"""
(() => {
  window.__PROBE = { installed: true, ts: Date.now() };
  // Kill the 47 rotating debugger stubs + any debugger statement traps
  const noop = function () {};
  try { Object.defineProperty(window, 'cxD0', { value: noop, writable: true }); } catch (e) {}
  // Neutralise Function/eval-based debugger bombs by filtering 'debugger'
  const rawEval = window.eval;
  window.eval = function (src) {
    if (typeof src === 'string' && src.indexOf('debugger') !== -1) return undefined;
    return rawEval.call(window, src);
  };
  const RawFunction = window.Function;
  window.Function = new Proxy(RawFunction, {
    apply(t, thisArg, args) {
      if (args.length && typeof args[args.length - 1] === 'string'
          && args[args.length - 1].indexOf('debugger') !== -1) return noop;
      return Reflect.apply(t, thisArg, args);
    },
    construct(t, args) {
      if (args.length && typeof args[args.length - 1] === 'string'
          && args[args.length - 1].indexOf('debugger') !== -1) return noop;
      return Reflect.construct(t, args);
    }
  });
  // Record every XHR/fetch the app performs (protocol ground truth)
  window.__NET = [];
  const of = window.fetch;
  window.fetch = function (input, init) {
    try {
      window.__NET.push({ kind: 'fetch', url: String(input && input.url ? input.url : input),
                          method: (init && init.method) || 'GET',
                          headers: init && init.headers ? JSON.parse(JSON.stringify(init.headers)) : null,
                          body: init && typeof init.body === 'string' ? init.body.slice(0, 4000) : null });
    } catch (e) {}
    return of.apply(this, arguments);
  };
  const oo = XMLHttpRequest.prototype.open;
  const os_ = XMLHttpRequest.prototype.send;
  const oh = XMLHttpRequest.prototype.setRequestHeader;
  XMLHttpRequest.prototype.open = function (m, u) { this.__probe = { kind: 'xhr', method: m, url: u, headers: {} }; return oo.apply(this, arguments); };
  XMLHttpRequest.prototype.setRequestHeader = function (k, v) {
    if (this.__probe) this.__probe.headers[k] = v; return oh.apply(this, arguments);
  };
  XMLHttpRequest.prototype.send = function (b) {
    if (this.__probe) { this.__probe.body = typeof b === 'string' ? b.slice(0, 6000) : null;
                        window.__NET.push(this.__probe); }
    return os_.apply(this, arguments);
  };
})();
"""


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(
            headless=True,
            executable_path=CHROME,
            proxy={"server": "http://127.0.0.1:10809"},
            args=["--ignore-certificate-errors", "--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        ctx = await b.new_context(ignore_https_errors=True,
                                  viewport={"width": 1920, "height": 1080})
        await ctx.add_init_script(INIT)
        pg = await ctx.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)[:200]))
        try:
            r = await pg.goto(TARGET + "/login", wait_until="commit", timeout=60000)
            print("[+] GET /login ->", r.status if r else None)
        except Exception as e:
            print("[!] goto warning:", type(e).__name__, str(e)[:120])
        try:
            await pg.wait_for_timeout(15000)
        except Exception:
            pass

        state = await pg.evaluate("""() => ({
            title: document.title,
            url: location.href,
            cxBox: typeof cxBox,
            cxReady: typeof cxReady,
            encrypt: typeof encrypt,
            decrypt: typeof decrypt,
            cxKeys: window.__cx ? Object.keys(window.__cx).join(',') : null,
            cxW: window.__cx ? String(window.__cx.w) : null,
            cxp: String(window.__cxp),
            cxwType: window.__cx && window.__cx.w !== undefined ? typeof window.__cx.w : 'n/a',
            wrid: sessionStorage.getItem('_wrid'),
            wts: sessionStorage.getItem('_wts'),
            inputs: Array.from(document.querySelectorAll('input')).map(i => ({
                name: i.name, type: i.type, placeholder: i.placeholder, id: i.id })),
            buttons: Array.from(document.querySelectorAll('button')).map(b => b.innerText.trim()).slice(0, 10),
            inputsCount: document.querySelectorAll('input').length,
            net: (window.__NET || []).length,
        })""")
        print(json.dumps(state, ensure_ascii=False, indent=2)[:2500])
        print("\n[pageerrors]", errors[:5])
        net = await pg.evaluate("""() => JSON.stringify((window.__NET||[]).slice(0,10).map(x => ({
            kind: x.kind, method: x.method, url: String(x.url).slice(0,120),
            hdrs: Object.keys(x.headers||{}).join(','), bodyLen: (x.body||'').length })))""")
        print("\n[net calls]", net[:1500])
        await b.close()


asyncio.run(main())
