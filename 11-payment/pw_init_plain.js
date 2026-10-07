window.__NET = [];
window.__PLAIN = [];
(function () {
  function rec(rec) { window.__NET.push(rec); }

  // ---- fetch: capture raw text, then the DECRYPTED json the app parses ----
  const of = window.fetch;
  window.fetch = function (input, init) {
    const r0 = {
      kind: 'fetch', url: String(input && input.url ? input.url : input),
      method: (init && init.method) || 'GET', headers: null, body: null,
      resp: null, status: null
    };
    try {
      r0.headers = init && init.headers ? JSON.parse(JSON.stringify(init.headers)) : null;
      r0.body = init && typeof init.body === 'string' ? init.body.slice(0, 30000) : null;
    } catch (e) {}
    rec(r0);
    return of.apply(this, arguments).then(function (r) {
      r0.status = r.status;
      // clone for raw text
      try { r.clone().text().then(function (t) { r0.resp = t.slice(0, 30000); }); } catch (e) {}
      // clone for decrypted json (post-interceptor the app sees plaintext)
      try {
        r.clone().json().then(function (j) {
          r0.plain = JSON.stringify(j).slice(0, 30000);
          window.__PLAIN.push({ url: r0.url, data: j });
        }).catch(function () {});
      } catch (e) {}
      return r;
    }, function (e) { r0.status = 'ERR'; throw e; });
  };

  // ---- XHR ----
  const oo = XMLHttpRequest.prototype.open;
  const os_ = XMLHttpRequest.prototype.send;
  const oh = XMLHttpRequest.prototype.setRequestHeader;
  XMLHttpRequest.prototype.open = function (m, u) {
    this.__p = { kind: 'xhr', method: m, url: u, headers: {} };
    return oo.apply(this, arguments);
  };
  XMLHttpRequest.prototype.setRequestHeader = function (k, v) {
    if (this.__p) this.__p.headers[k] = v;
    return oh.apply(this, arguments);
  };
  XMLHttpRequest.prototype.send = function (b) {
    if (this.__p) {
      this.__p.body = typeof b === 'string' ? b.slice(0, 30000) : null;
      const self = this;
      this.addEventListener('load', function () {
        try {
          self.__p.status = self.status;
          let t = String(self.responseText);
          self.__p.resp = t.slice(0, 30000);
          // the app's interceptor rewrites responseText to plaintext JSON;
          // try to interpret whatever is there now
          try {
            const j = JSON.parse(t);
            self.__p.plain = JSON.stringify(j).slice(0, 30000);
            window.__PLAIN.push({ url: self.__p.url, data: j });
          } catch (e) {}
        } catch (e) {}
      });
      rec(this.__p);
    }
    return os_.apply(this, arguments);
  };
})();
