window.__NET = [];
window.__PLAIN = [];
window.__KEYS = [];

(function () {
  // ---- Axios hooks: the app stores per-request crypto material on the config ----
  // Intercept adapter so we can read config.__azhifuRsaAesKey / __cxRaw and
  // decrypt the raw body ourselves using the browser's own WebCrypto.
  const origFetch = window.fetch;

  // Sniff every JSON.parse / Response.json for the {v,p,q,t} envelope and
  // remember it, so we can decrypt afterwards with a recovered key.
  const oParse = JSON.parse;
  window.JSON.parse = function (t, r) {
    const v = oParse.call(this, t, r);
    try {
      if (v && typeof v === 'object' && v.v === 3 && v.p && v.q) {
        window.__NET.push({ kind: 'envelope', env: v, t: Date.now() });
      }
    } catch (e) {}
    return v;
  };

  const oo = XMLHttpRequest.prototype.open;
  const os_ = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function (m, u) { this.__u = u; this.__m = m; return oo.apply(this, arguments); };
  XMLHttpRequest.prototype.send = function (b) {
    const self = this;
    this.addEventListener('load', function () {
      try {
        const raw = self.responseText;
        let j = null;
        try { j = oParse(raw); } catch (e) {}
        window.__NET.push({
          kind: 'xhr', method: self.__m, url: String(self.__u),
          status: self.status, raw: String(raw).slice(0, 30000),
          plain: j
        });
      } catch (e) {}
    });
    return os_.apply(this, arguments);
  };
})();
