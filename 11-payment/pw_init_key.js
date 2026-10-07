window.__NET = [];
window.__ENV = [];      // every {v,p,q,t} envelope seen
window.__PLAIN = [];    // every parsed object that is NOT an envelope
window.__KEYS = [];     // recovered AES keys

(function () {
  const oParse = JSON.parse;
  window.JSON.parse = function (text, reviver) {
    const v = oParse.call(this, text, reviver);
    try {
      if (v && typeof v === 'object') {
        if (v.v === 3 && typeof v.p === 'string' && typeof v.q === 'string') {
          window.__ENV.push({ env: v, at: Date.now() });
        } else if (!Array.isArray(v)) {
          window.__PLAIN.push({ data: v, at: Date.now() });
        }
      }
    } catch (e) {}
    return v;
  };

  // Capture the AES key material the app attaches to outgoing requests:
  // azhifuRsaWrapGetKey sets e.__cxRaw (Uint8Array) and e.__azhifuRsaAesKey (CryptoKey)
  const of = window.fetch;
  window.fetch = function (input, init) {
    const cfg = init || {};
    let rawHex = null;
    try {
      if (cfg.__cxRaw) {
        rawHex = Array.from(new Uint8Array(cfg.__cxRaw))
                       .map(b => b.toString(16).padStart(2, '0')).join('');
      }
    } catch (e) {}
    const rec = {
      kind: 'fetch',
      url: String(input && input.url ? input.url : input),
      method: cfg.method || 'GET',
      hasRaw: !!rawHex, rawHex: rawHex,
      hasAesKey: !!cfg.__azhifuRsaAesKey,
      headers: (function () { try { return JSON.parse(JSON.stringify(cfg.headers || {})); } catch (e) { return null; } })(),
      body: typeof cfg.body === 'string' ? cfg.body.slice(0, 30000) : null,
      status: null, resp: null
    };
    if (rawHex) window.__KEYS.push({ url: rec.url, rawHex: rawHex });
    window.__NET.push(rec);
    return of.apply(this, arguments).then(function (r) {
      rec.status = r.status;
      try { r.clone().text().then(function (t) { rec.resp = t.slice(0, 30000); }); } catch (e) {}
      return r;
    });
  };
})();
