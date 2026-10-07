window.__NET = [];
window.__PLAIN = [];

(function () {
  // The app's response interceptor replaces the XHR body with decrypted JSON.
  // Capture the FINAL value written to responseText — that is the plaintext.
  const d = Object.getOwnPropertyDescriptor(XMLHttpRequest.prototype, 'responseText');
  if (d && d.get) {
    Object.defineProperty(XMLHttpRequest.prototype, 'responseText', {
      configurable: true,
      get: function () {
        const v = d.get.call(this);
        try {
          if (v && v.length && v.charCodeAt(0) === 123 /* '{' */) {
            const j = JSON.parse(v);
            // plaintext business payloads never carry the {v,p,q,t} envelope
            if (j && !(j.v !== undefined && j.p !== undefined && j.q !== undefined)) {
              const u = this.__p ? this.__p.url : 'unknown';
              if (!this.__logged) {
                this.__logged = true;
                window.__PLAIN.push({ url: u, data: j });
              }
            }
          }
        } catch (e) {}
        return v;
      }
    });
  }

  const oo = XMLHttpRequest.prototype.open;
  const os_ = XMLHttpRequest.prototype.send;
  const oh = XMLHttpRequest.prototype.setRequestHeader;
  XMLHttpRequest.prototype.open = function (m, u) {
    this.__p = { kind: 'xhr', method: m, url: u, headers: {}, status: null, resp: null };
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
        self.__p.status = self.status;
        try { self.__p.resp = String(d ? d.get.call(self) : self.responseText).slice(0, 30000); }
        catch (e) {}
      });
      window.__NET.push(this.__p);
    }
    return os_.apply(this, arguments);
  };

  const of = window.fetch;
  window.fetch = function (input, init) {
    const r0 = { kind: 'fetch', url: String(input && input.url ? input.url : input),
                 method: (init && init.method) || 'GET', headers: null, body: null };
    try {
      r0.headers = init && init.headers ? JSON.parse(JSON.stringify(init.headers)) : null;
      r0.body = init && typeof init.body === 'string' ? init.body.slice(0, 30000) : null;
    } catch (e) {}
    window.__NET.push(r0);
    return of.apply(this, arguments);
  };
})();
