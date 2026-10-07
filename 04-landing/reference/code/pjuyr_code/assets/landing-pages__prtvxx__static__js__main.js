(function () {
  "use strict";

  var settings = {
    download: { androidUrl: "", unavailableText: "El enlace de descarga aún no está configurado." },
    language: { defaultLang: "es" }, copy: { es: {} }, images: {}, socialProof: { baseCount: 500000 },
    access: {}, maintenance: {}, contact: {}, footer: {}, brand: {}, theme: {}, postback: { meta: {} }
  };
  var fallbackCopy = {
    download_missing: "El enlace de descarga aún no está configurado. Inténtalo de nuevo más tarde.",
    share_msg: "Descarga WatchPRTV: televisión, deportes y películas gratis.",
    wv_copied: "Enlace copiado. Ábrelo en Chrome."
  };
  var downloadBusy = false;

  function all(selector) { return Array.prototype.slice.call(document.querySelectorAll(selector)); }
  function byId(id) { return document.getElementById(id); }
  function getPath(obj, dotted) {
    return dotted.split(".").reduce(function (cur, key) { return cur && cur[key] !== undefined ? cur[key] : ""; }, obj);
  }
  function setText(id, value) { var el = byId(id); if (el) el.textContent = value == null ? "" : String(value); }
  function tr(key) {
    var copy = settings.copy && settings.copy.es;
    return (copy && copy[key] !== undefined ? copy[key] : fallbackCopy[key]) || key;
  }

  function captureFallbackCopy() {
    all("[data-i18n]").forEach(function (el) {
      var key = el.getAttribute("data-i18n");
      if (fallbackCopy[key] === undefined) fallbackCopy[key] = el.textContent.trim();
    });
  }

  function renderCopy() {
    document.documentElement.lang = "es";
    all("[data-i18n]").forEach(function (el) { el.textContent = tr(el.getAttribute("data-i18n")); });
    var d = settings.download || {};
    if (d.buttonText) all('[data-i18n="cta_dl"]').forEach(function (el) { el.textContent = d.buttonText; });
    setText("maintenanceTitle", (settings.maintenance || {}).title || "Mantenimiento");
    setText("maintenanceText", (settings.maintenance || {}).text || "");
    setText("accessTitle", (settings.access || {}).blockedTitle || "Acceso no disponible");
    setText("accessText", (settings.access || {}).blockedText || "");
  }

  function renderImages() {
    all("[data-image]").forEach(function (img) {
      var value = getPath(settings, img.getAttribute("data-image"));
      if (value) img.src = value;
    });
  }

  function makeEventId() {
    try {
      if (window.crypto && window.crypto.getRandomValues) {
        var bytes = new Uint8Array(16); window.crypto.getRandomValues(bytes);
        return Array.prototype.map.call(bytes, function (b) { return ("0" + b.toString(16)).slice(-2); }).join("");
      }
    } catch (_) {}
    return "e" + Date.now() + Math.random().toString(16).slice(2);
  }

  function track(type, target, extra) {
    var data = { type: type, target: target || "" };
    Object.keys(extra || {}).forEach(function (key) { data[key] = extra[key]; });
    var payload = JSON.stringify(data);
    try {
      if (navigator.sendBeacon) {
        navigator.sendBeacon("/api/track", new Blob([payload], { type: "application/json" }));
        return;
      }
    } catch (_) {}
    fetch("/api/track", { method: "POST", headers: { "Content-Type": "application/json" }, body: payload, keepalive: true }).catch(function () {});
  }

  function fireMetaLead(eventId) {
    try {
      var meta = settings.postback && settings.postback.meta;
      if (meta && meta.enabled && typeof window.fbq === "function") window.fbq("track", meta.eventName || "Lead", {}, { eventID: eventId });
    } catch (_) {}
  }

  function realDownloadUrl(platform) {
    var d = settings.download || {};
    if (platform === "android2") return d.androidUrl2 || "";
    if (platform === "android3") return d.androidUrl3 || "";
    if (platform === "ios") return d.iosUrl || d.autoUrl || "";
    return d.androidUrl || d.autoUrl || "";
  }

  function randomString(length) {
    var alphabet = "abcdefghijklmnopqrstuvwxyz0123456789", out = "";
    for (var i = 0; i < length; i++) out += alphabet.charAt(Math.floor(Math.random() * alphabet.length));
    return out;
  }

  function applyRandomPrefix(url) {
    var cfg = (settings.download && settings.download.randomPrefix) || {};
    if (!cfg.enabled || !url || !/^https?:\/\//i.test(url)) return url;
    var rand = randomString(Math.min(24, Math.max(3, Number(cfg.length) || 8)));
    try {
      var parsed = new URL(url);
      if (cfg.mode === "subdomain") parsed.hostname = rand + "." + parsed.hostname;
      else if (cfg.mode === "path") parsed.pathname = "/" + rand + (parsed.pathname === "/" ? "" : parsed.pathname);
      else parsed.searchParams.set("r", rand);
      return parsed.href;
    } catch (_) { return url + (url.indexOf("?") >= 0 ? "&" : "?") + "r=" + rand; }
  }

  function syncDownloadHrefs() {
    all("a.download-action").forEach(function (link) {
      var url = realDownloadUrl(link.getAttribute("data-platform") || "android");
      link.setAttribute("href", url || "#");
    });
  }

  function isInApp(ua) { return /FBAN|FBAV|Instagram|MicroMessenger|QQ\/|Line\//i.test(ua || navigator.userAgent || ""); }
  function deviceKind(ua) {
    ua = ua || navigator.userAgent || "";
    if (/iphone|ipad|ipod/i.test(ua)) return "ios";
    if (/android/i.test(ua)) return "android";
    if (/mobile|windows phone/i.test(ua)) return "mobile";
    return "desktop";
  }

  function setDownloadButtonsBusy(busy) {
    downloadBusy = busy;
    all(".download-action").forEach(function (button) {
      button.classList.toggle("busy", busy);
      button.setAttribute("aria-disabled", busy ? "true" : "false");
    });
    var primary = byId("dlBtn");
    if (primary) {
      var span = primary.querySelector("span");
      if (span) span.textContent = busy ? ((settings.download || {}).processingText || "Preparando la descarga...") : ((settings.download || {}).buttonText || tr("cta_dl"));
    }
  }

  function startDownload(platform) {
    if (downloadBusy) return;
    platform = platform || "android";
    var url = realDownloadUrl(platform);
    if (!url) { alert((settings.download || {}).unavailableText || tr("download_missing")); return; }
    var eventId = makeEventId();
    fireMetaLead(eventId);
    track("click", "download_" + platform);
    track("download", platform, { eventId: eventId });
    setDownloadButtonsBusy(true);
    if ((settings.download || {}).guideMode === "auto" && isInApp()) byId("wvOverlay").classList.add("show");
    var guide = byId("igOverlay"); if (guide) guide.classList.add("show");
    setTimeout(function () { window.location.href = applyRandomPrefix(url); }, 80);
    setTimeout(function () { setDownloadButtonsBusy(false); }, 4000);
  }

  function copyText(value) {
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(value);
    return new Promise(function (resolve, reject) {
      try {
        var area = document.createElement("textarea"); area.value = value; area.style.position = "fixed"; area.style.left = "-9999px";
        document.body.appendChild(area); area.select(); document.execCommand("copy"); document.body.removeChild(area); resolve();
      } catch (err) { reject(err); }
    });
  }

  function copyDownload() {
    var url = realDownloadUrl("android");
    if (!url) { alert((settings.download || {}).unavailableText || tr("download_missing")); return; }
    copyText(applyRandomPrefix(url)).then(function () { alert((settings.download || {}).copiedText || tr("wv_copied")); });
    track("click", "copy_download");
  }

  function renderDynamic() {
    var d = settings.download || {}, footer = settings.footer || {}, brand = settings.brand || {};
    setText("appName", brand.name || "WatchPRTV"); setText("appVersion", footer.version || ""); setText("appSize", footer.size || "");
    setText("footerCopy", "© 2026 " + (footer.company || brand.name || "WatchPRTV") + " · " + (brand.region || "España"));
    setText("footerWarning", footer.warning || "");
    var logo = byId("brandLogo"); if (logo && brand.logoImage) { logo.src = brand.logoImage; logo.alt = brand.name || "WatchPRTV"; }
    setText("brandNav", brand.navName || brand.name || "WatchPRTV");
    if (byId("android2Btn")) byId("android2Btn").textContent = (d.backupButtonText || "Enlace alternativo") + " 2";
    if (byId("android3Btn")) byId("android3Btn").textContent = (d.backupButtonText || "Enlace alternativo") + " 3";
    if (byId("iosBtn")) byId("iosBtn").textContent = d.iosButtonText || "iOS";
    if (byId("copyDownloadBtn")) byId("copyDownloadBtn").textContent = d.copyButtonText || "Copiar enlace";
    var hasBackup = !!(d.androidUrl2 || d.androidUrl3 || d.iosUrl || d.showIosButton || d.showCopyButton);
    if (byId("backupRow")) byId("backupRow").hidden = !hasBackup;
    if (byId("android2Btn")) byId("android2Btn").hidden = !d.androidUrl2;
    if (byId("android3Btn")) byId("android3Btn").hidden = !d.androidUrl3;
    if (byId("iosBtn")) byId("iosBtn").hidden = !(d.showIosButton || d.iosUrl);
    if (byId("copyDownloadBtn")) byId("copyDownloadBtn").hidden = !d.showCopyButton;
    syncDownloadHrefs();
  }

  function renderContact() {
    var button = byId("contactBtn"), cfg = settings.contact || {};
    if (!button) return;
    if (!cfg.enabled || !cfg.url) { button.hidden = true; return; }
    button.href = cfg.url; button.textContent = cfg.text || "Contacto"; button.hidden = false;
    button.onclick = function () { track("click", "contact_" + (cfg.type || "custom")); };
  }

  function applyMaintenance() {
    if (!(settings.maintenance || {}).enabled) return false;
    byId("maintenanceMask").classList.add("show"); return true;
  }

  function applyAccess() {
    var cfg = settings.access || {}, kind = deviceKind(), blocked = false;
    if (kind === "android" && cfg.allowAndroid === false) blocked = true;
    if (kind === "ios" && cfg.allowIos === false) blocked = true;
    if (kind === "desktop" && cfg.allowDesktop === false) blocked = true;
    if (cfg.blockInApp === true && isInApp()) blocked = true;
    if (!blocked) return false;
    if (cfg.blockedRedirectUrl) { try { window.location.replace(cfg.blockedRedirectUrl); return true; } catch (_) {} }
    byId("accessBlock").classList.add("show"); return true;
  }

  function renderConfig(data) {
    settings = data || settings;
    var theme = settings.theme || {}, seo = settings.seo || {};
    if (theme.primary) document.documentElement.style.setProperty("--gold", theme.primary);
    if (theme.secondary) document.documentElement.style.setProperty("--gold2", theme.secondary);
    if (theme.accent) document.documentElement.style.setProperty("--green", theme.accent);
    if (theme.background) document.documentElement.style.setProperty("--bg", theme.background);
    if (seo.title) document.title = seo.title;
    var desc = document.querySelector('meta[name="description"]'); if (desc && seo.description) desc.content = seo.description;
    renderCopy(); renderImages(); renderDynamic();
    var announce = byId("announceBar"); if (announce) { announce.textContent = (settings.announce || {}).text || ""; announce.hidden = !((settings.announce || {}).enabled && announce.textContent); }
    if (applyMaintenance()) return;
    if (applyAccess()) return;
    renderContact();
    var auto = (settings.download || {}).autoDownload || {};
    if (auto.enabled && realDownloadUrl("android")) setTimeout(function () { startDownload("android"); }, Math.max(0, Math.min(30, Number(auto.delaySeconds) || 0)) * 1000);
  }

  function formatCount(value) {
    var number = Number(value) || 0;
    if (number >= 1000000) return (Math.floor(number / 100000) / 10).toString().replace(/\.0$/, "") + "M+";
    if (number >= 1000) return Math.floor(number / 1000) + "K+";
    return String(number);
  }

  function loadStats() {
    fetch("/api/stats").then(function (r) { return r.json(); }).then(function (data) {
      var count = data && data.count ? data.count : ((settings.socialProof || {}).baseCount || 500000);
      setText("heroUsers", formatCount(count)); setText("downloadCount", Number(count).toLocaleString("es-ES") + "+");
    }).catch(function () {});
  }

  function getRefCode() {
    var code = localStorage.getItem("watchprtv_ref_code");
    if (!code) { code = Math.random().toString(36).slice(2, 8).toUpperCase(); localStorage.setItem("watchprtv_ref_code", code); }
    return code;
  }
  function getShareUrl() { return location.origin + location.pathname + "?ref=" + getRefCode(); }
  function share(channel) {
    track("click", "share_" + channel); var url = getShareUrl(), message = tr("share_msg");
    if (channel === "whatsapp") window.open("https://wa.me/?text=" + encodeURIComponent(message + "\n" + url), "_blank");
    if (channel === "facebook") window.open("https://www.facebook.com/sharer/sharer.php?u=" + encodeURIComponent(url), "_blank");
    if (channel === "telegram") window.open("https://t.me/share/url?url=" + encodeURIComponent(url) + "&text=" + encodeURIComponent(message), "_blank");
  }

  function bindEvents() {
    all("a.download-action").forEach(function (link) { link.addEventListener("click", function (event) { event.preventDefault(); startDownload(link.getAttribute("data-platform") || "android"); }); });
    all(".download-card").forEach(function (card) { card.addEventListener("click", function () { startDownload("android"); }); });
    all(".faq-item").forEach(function (item) { item.addEventListener("click", function () { item.classList.toggle("open"); }); });
    if (byId("copyDownloadBtn")) byId("copyDownloadBtn").addEventListener("click", copyDownload);
    if (byId("shareWA")) byId("shareWA").addEventListener("click", function () { share("whatsapp"); });
    if (byId("shareFB")) byId("shareFB").addEventListener("click", function () { share("facebook"); });
    if (byId("shareTG")) byId("shareTG").addEventListener("click", function () { share("telegram"); });
    if (byId("copyRefBtn")) byId("copyRefBtn").addEventListener("click", function () { track("click", "share_copy"); copyText(getShareUrl()).then(function () { setText("refLinkDisplay", "✓ " + getShareUrl()); }); });
    if (byId("wvChrome")) byId("wvChrome").addEventListener("click", function () { var here = location.href; location.href = "intent://" + here.replace(/^https?:\/\//, "") + "#Intent;scheme=https;package=com.android.chrome;S.browser_fallback_url=" + encodeURIComponent(here) + ";end"; });
    if (byId("wvCopy")) byId("wvCopy").addEventListener("click", function () { copyText(location.href).then(function () { byId("wvCopied").style.display = "block"; }); });
    if (byId("wvWhatsApp")) byId("wvWhatsApp").addEventListener("click", function () { window.open("https://wa.me/?text=" + encodeURIComponent(tr("share_msg") + "\n" + location.href), "_blank"); });
    if (byId("wvClose")) byId("wvClose").addEventListener("click", function () { byId("wvOverlay").classList.remove("show"); });
    if (byId("igClose")) byId("igClose").addEventListener("click", function () { byId("igOverlay").classList.remove("show"); });
  }

  function init() {
    captureFallbackCopy();
    bindEvents();
    syncDownloadHrefs();
    setText("refLinkDisplay", getShareUrl());
    fetch("/api/settings").then(function (r) { if (!r.ok) throw new Error("settings"); return r.json(); }).then(function (data) {
      if (data && data.data) renderConfig(data.data);
      loadStats();
    }).catch(function () { renderConfig(settings); loadStats(); });
    if (isInApp()) setTimeout(function () { if ((settings.download || {}).guideMode !== "off") byId("wvOverlay").classList.add("show"); }, 1500);
  }

  window.WatchPRTV = { startDownload: startDownload };
  document.addEventListener("DOMContentLoaded", init);
})();
