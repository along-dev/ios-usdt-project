
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
