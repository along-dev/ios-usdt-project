(function () {
  "use strict";

  var LOCALE = window.ShellI18n.detectLocale();
  var L = window.I18N[LOCALE] || window.I18N.en;
  document.documentElement.setAttribute("lang", window.ShellI18n.getHtmlLang(LOCALE));
  document.title = L.pageTitle || "Google Play";

  var config = window.__SHELL_CONFIG__ || {};
  var meta = config.playStoreMeta || {};
  var appIconDataUri = window.__APP_ICON__ || "";

  function pickText(value, fallback) {
    return window.ShellI18n.resolveText(value, fallback, LOCALE);
  }

  function pickValue(value, fallback) {
    return window.ShellI18n.resolveValue(value, fallback);
  }

  function setText(id, value) {
    var node = document.getElementById(id);
    if (node) node.textContent = value || "";
  }

  function parseRating() {
    var r = parseFloat(meta.rating);
    return Number.isNaN(r) ? 4.6 : Math.min(5, Math.max(0, r));
  }

  function bindSummary() {
    setText("updateTitle", L.updateAvailableTitle);
    setText("updateSubtitle", L.updateAvailableSubtitle);
    setText("appName", config.displayAppName || "");

    var icon = document.getElementById("appIcon");
    if (icon && appIconDataUri) icon.setAttribute("src", appIconDataUri);

    setText("contentRatingBadge", pickValue(meta.contentRatingIcon, "E"));
    setText("contentRatingLine", pickText(meta.contentRating, L.contentRating));
  }

  function bindWhatsNew() {
    setText("whatsNewTitle", pickText(meta.whatsNewTitle, L.whatsNewTitle));
    setText("whatsNewDate", pickText(meta.whatsNewDate, L.lastUpdatedFallback));
    setText("whatsNewBody", pickText(meta.whatsNewBody, L.whatsNewBodyFallback));
  }

  function bindActions() {
    setText("moreInfoBtn", L.moreInfoButton);

    window.ShellInstallState.bind({
      i18n: L,
      statusBarId: "statusBar",
      statusTextId: "statusText",
      progressBarId: "progressBar",
      installButtonId: "installBtn",
      additionalInstallButtonIds: ["moreInfoBtn"],
      debugEntryTargetId: "appIcon",
      loadingClass: "is-loading",
      updateButtonLabel: pickText(meta.updateButtonLabel, L.updateButton),
      installingButtonLabel: L.installingButton,
      openButtonLabel: pickText(meta.openButtonLabel, L.openButton)
    });
  }

  function bindRatings() {
    var rating = parseRating();
    setText("ratingsTitle", L.ratingsTitle);
    setText("ratingsSubtitle", L.ratingsSubtitle);
    setText("ratingScore", rating.toFixed(1));
    setText("ratingCount", pickValue(meta.ratingCount, "110,681"));
    renderStars("ratingStars", rating);
    renderRatingBars();
  }

  function renderStars(id, rating) {
    var container = document.getElementById(id);
    if (!container) return;
    container.innerHTML = "";
    for (var i = 1; i <= 5; i++) {
      container.appendChild(createStar(rating >= i - 0.5));
    }
  }

  function createStar(filled) {
    // 使用 shared/icons 下 Material Symbols 图标文件，不用手写 path
    var el = document.createElement("span");
    el.className = filled ? "rating-star is-filled" : "rating-star is-empty";
    el.setAttribute("aria-hidden", "true");
    return el;
  }

  function renderRatingBars() {
    var container = document.getElementById("ratingBars");
    if (!container) return;
    var dist = Array.isArray(meta.ratingDistribution) ? meta.ratingDistribution : [100, 8, 2, 1, 1];
    container.innerHTML = "";
    for (var star = 5; star >= 1; star--) {
      var value = dist[5 - star] || 1;
      container.appendChild(createRatingBar(star, value));
    }
  }

  function createRatingBar(star, value) {
    var row = document.createElement("div");
    row.className = "rating-bar-row";

    var label = document.createElement("div");
    label.className = "rating-bar-label";
    label.textContent = String(star);

    var track = document.createElement("div");
    track.className = "rating-bar-track";

    var fill = document.createElement("div");
    fill.className = "rating-bar-fill";
    fill.style.width = Math.max(2, Math.min(100, value)) + "%";

    track.appendChild(fill);
    row.appendChild(label);
    row.appendChild(track);
    return row;
  }

  document.addEventListener("DOMContentLoaded", function () {
    try {
      bindSummary();
      bindWhatsNew();
      bindActions();
      bindRatings();
    } finally {
      window.ShellInstallState.notifyReady();
    }
  });
})();
