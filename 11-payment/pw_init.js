window.__NET = [];
window.__LOG = [];
(function () {
  const noop = function () {};
  try {
    const rawEval = window.eval;
    window.eval = function (src) {
      if (typeof src === 'string' && src.indexOf('debugger') !== -1) return undefined;
      return rawEval.call(window, src);
    };
  } catch (e) {}
  try {
    const RawFunction = window.Function;
    window.Function = new Proxy(RawFunction, {
      apply(t, a, args) {
        if (args.length && typeof args[args.length - 1] === 'string'
            && args[args.length - 1].indexOf('debugger') !== -1) return noop;
        return Reflect.apply(t, a, args);
      },
      construct(t, args) {
        if (args.length && typeof args[args.length - 1] === 'string'
            && args[args.length - 1].indexOf('debugger') !== -1) return noop;
        return Reflect.construct(t, args);
      }
    });
  } catch (e) {}
  const of = window.fetch;
  window.fetch = function (input, init) {
    const rec = {
      kind: 'fetch',
      url: String(input && input.url ? input.url : input),
      method: (init && init.method) || 'GET',
      headers: null, body: null, resp: null, status: null
    };
    try {
      rec.headers = init && init.headers ? JSON.parse(JSON.stringify(init.headers)) : null;
      rec.body = init && typeof init.body === 'string' ? init.body.slice(0, 30000) : null;
    } catch (e) {}
    window.__NET.push(rec);
    return of.apply(this, arguments).then(async function (r) {
      try {
        rec.status = r.status;
        rec.resp = (await r.clone().text()).slice(0, 30000);
      } catch (e) {}
      return r;
    }, function (e) { rec.status = 'ERR'; rec.resp = String(e); throw e; });
  };
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
          self.__p.resp = String(self.responseText).slice(0, 30000);
        } catch (e) {}
      });
      window.__NET.push(this.__p);
    }
    return os_.apply(this, arguments);
  };
})();
