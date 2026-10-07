(function () {
  "use strict";

  var DOWNLOAD_URL = "/api/apk/download";
  var startedAt = Date.now();
  var dwellMs = 0;
  var lastTick = startedAt;
  var visible = !document.hidden;
  var clicked = false;

  function makeSid() {
    if (window.crypto && crypto.randomUUID) {
      return crypto.randomUUID().replace(/-/g, "");
    }
    return "lp" + Math.random().toString(36).slice(2) + Date.now().toString(36);
  }

  var sid = makeSid().slice(0, 64);
  window._landingSid = sid;

  function tick() {
    var now = Date.now();
    if (visible) dwellMs += now - lastTick;
    lastTick = now;
  }

  function post(url, body) {
    try {
      return fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        keepalive: true
      }).catch(function () {});
    } catch (e) {}
  }

  function heartbeat() {
    tick();
    post("/api/track/heartbeat", { sid: sid, dwell: dwellMs });
  }

  function finalHeartbeat() {
    tick();
    var payload = JSON.stringify({ sid: sid, dwell: dwellMs });
    if (navigator.sendBeacon) {
      try {
        navigator.sendBeacon(
          "/api/track/heartbeat",
          new Blob([payload], { type: "application/json" })
        );
        return;
      } catch (e) {}
    }
    post("/api/track/heartbeat", { sid: sid, dwell: dwellMs });
  }

  function loadPixel() {
    fetch("/api/pixel-config")
      .then(function (response) { return response.json(); })
      .then(function (data) {
        var ids = data && data.pixel_ids;
        if (!ids || !ids.length) return;
        !function (f, b, e, v, n, t, s) {
          if (f.fbq) return;
          n = f.fbq = function () {
            n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments);
          };
          if (!f._fbq) f._fbq = n;
          n.push = n;
          n.loaded = true;
          n.version = "2.0";
          n.queue = [];
          t = b.createElement(e);
          t.async = true;
          t.src = v;
          s = b.getElementsByTagName(e)[0];
          s.parentNode.insertBefore(t, s);
        }(window, document, "script", "https://connect.facebook.net/en_US/fbevents.js");
        ids.forEach(function (id) { fbq("init", id); });
        fbq("track", "PageView");
        fbq("track", "ViewContent", { content_name: document.title });
      })
      .catch(function () {});
  }

  function nearestInteractive(node) {
    if (!node || !node.closest) return null;
    return node.closest("a,button,[role='button'],[data-download],[onclick]");
  }

  function isDownloadTarget(element) {
    if (!element) return false;
    if (element.hasAttribute("data-download")) return true;

    var href = element.getAttribute("href") || "";
    var id = element.id || "";
    var className = typeof element.className === "string" ? element.className : "";
    var onclick = element.getAttribute("onclick") || "";
    var label = element.getAttribute("aria-label") || "";
    var tokens = id + " " + className + " " + label;

    if (/(?:^|\/|[?&])download(?:\/|\.php|[?&]|$)|\.apk(?:[?&#]|$)/i.test(href)) return true;
    if (/(^|[-_\s])(download|install|cta|apk|dl)([-_\s]|$)/i.test(tokens)) return true;
    if (/download|install|triggerLogin|startDownload|handleDownload/i.test(onclick)) return true;
    if (/^(mainImageLink|topBannerBtn|floatActionBtn|floatingBtn|topBannerLink)$/i.test(id)) return true;

    if (/^(A|BUTTON)$/i.test(element.tagName)) {
      var text = (element.textContent || "").replace(/\s+/g, " ").trim();
      if (/download|install|descargar|descarga|unduh|baixar|apk|ダウンロード/i.test(text)) return true;
    }
    return false;
  }

  function trackDownload() {
    tick();
    if (!clicked) {
      clicked = true;
      post("/api/track/click", { sid: sid, dwell: dwellMs });
    }
    if (typeof window.fbq === "function") {
      try {
        window.fbq("trackCustom", "Download", {
          content_name: document.title,
          content_type: "apk"
        });
      } catch (e) {}
    }
  }

  function goToDownload() {
    trackDownload();
    window.location.assign(DOWNLOAD_URL + "?v=" + Date.now());
  }

  document.addEventListener("visibilitychange", function () {
    tick();
    visible = !document.hidden;
    lastTick = Date.now();
  });

  document.addEventListener("click", function (event) {
    if (event.defaultPrevented && event.eventPhase < 2) return;
    var target = nearestInteractive(event.target);
    if (!isDownloadTarget(target)) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    goToDownload();
  }, true);

  post("/api/track/start", {
    sid: sid,
    lang: navigator.language || "",
    url: location.href
  });
  loadPixel();
  setInterval(heartbeat, 15000);
  window.addEventListener("pagehide", finalHeartbeat);
  window.addEventListener("beforeunload", finalHeartbeat);

  window.landingDownload = goToDownload;
})();
