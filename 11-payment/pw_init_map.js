window.__NET = [];
window.__ENV = [];
window.__PLAIN = [];

(function () {
  // Track the most recent fetch/XHR so a decrypted JSON.parse can be tied to a URL.
  window.__LAST_URL = null;

  const oParse = JSON.parse;
  window.JSON.parse = function (text, reviver) {
    const v = oParse.call(this, text, reviver);
    try {
      if (v && typeof v === 'object' && !Array.isArray(v)) {
        if (v.v === 3 && typeof v.p === 'string' && typeof v.q === 'string') {
          window.__ENV.push({ url: window.__LAST_URL, env: v, at: Date.now() });
        } else {
          window.__PLAIN.push({ url: window.__LAST_URL, data: v, at: Date.now() });
        }
      }
    } catch (e) {}
    return v;
  };

  const of = window.fetch;
  window.fetch = function (input, init) {
    const url = String(input && input.url ? input.url : input);
    const cfg = init || {};
    window.__LAST_URL = url;
    const rec = {
      kind: 'fetch', url: url, method: cfg.method || 'GET',
      headers: (function () { try { return JSON.parse(JSON.stringify(cfg.headers || {})); } catch (e) { return null; } })(),
      body: typeof cfg.body === 'string' ? cfg.body.slice(0, 30000) : null,
      status: null, resp: null
    };
    window.__NET.push(rec);
    return of.apply(this, arguments).then(function (r) {
      rec.status = r.status;
      try {
        r.clone().text().then(function (t) {
          rec.resp = t.slice(0, 30000);
          let j = null;
          try { j = oParse(t); } catch (e) {}
          if (j && typeof j === 'object' && !Array.isArray(j)) {
            if (j.v === 3 && typeof j.p === 'string') {
              rec.envelope = j;
            } else {
              rec.plain = JSON.stringify(j).slice(0, 30000);
              window.__PLAIN.push({ url: url, data: j, at: Date.now() });
            }
          }
        });
      } catch (e) {}
      return r;
    });
  };
})();
