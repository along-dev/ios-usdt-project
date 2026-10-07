(function (global) {
  "use strict";

  var DEFAULT_LOCALE = "en";
  var HTML_LANG_MAP = {
    zh: "zh-CN",
    "zh-tw": "zh-TW",
    en: "en",
    hi: "hi",
    es: "es",
    "es-mx": "es-MX",
    pt: "pt",
    "pt-br": "pt-BR",
    ar: "ar",
    id: "id",
    ja: "ja",
    my: "my",
    fr: "fr",
    de: "de",
    ko: "ko",
    th: "th",
    vi: "vi",
    tr: "tr",
    ms: "ms"
  };
  var LOCALE_ALIASES = {
    zh: "zh",
    "zh-cn": "zh",
    "zh-sg": "zh",
    "zh-hans": "zh",
    "zh-tw": "zh-tw",
    "zh-hk": "zh-tw",
    "zh-mo": "zh-tw",
    "zh-hant": "zh-tw",
    en: "en",
    hi: "hi",
    es: "es",
    "es-es": "es",
    "es-mx": "es-mx",
    "es-419": "es-mx",
    "es-us": "es-mx",
    pt: "pt",
    "pt-pt": "pt",
    "pt-br": "pt-br",
    ar: "ar",
    id: "id",
    in: "id",
    ja: "ja",
    my: "my",
    "my-mm": "my",
    fr: "fr",
    de: "de",
    ko: "ko",
    th: "th",
    vi: "vi",
    tr: "tr",
    ms: "ms"
  };

  function addCandidate(candidates, value) {
    if (!value) {
      return;
    }
    if (Array.isArray(value)) {
      value.forEach(function (item) {
        addCandidate(candidates, item);
      });
      return;
    }
    if (typeof value === "string" && value.trim()) {
      candidates.push(value);
    }
  }

  function normalizeLocale(value) {
    if (typeof value !== "string" || !value.trim()) {
      return "";
    }
    var raw = value.toLowerCase().replace(/_/g, "-");
    if (LOCALE_ALIASES[raw]) {
      return LOCALE_ALIASES[raw];
    }
    var primary = raw.split("-")[0];
    if (LOCALE_ALIASES[primary]) {
      return LOCALE_ALIASES[primary];
    }
    return "";
  }

  function collectLocaleCandidates() {
    var candidates = [];
    var runtime = global.__SHELL_RUNTIME__;
    if (runtime && typeof runtime === "object") {
      addCandidate(candidates, runtime.locale);
      addCandidate(candidates, runtime.locales);
    }
    addCandidate(candidates, global.__SHELL_LOCALE__);

    var nav = global.navigator || {};
    addCandidate(candidates, nav.languages);
    addCandidate(candidates, nav.language);
    addCandidate(candidates, nav.userLanguage);
    addCandidate(candidates, nav.browserLanguage);
    addCandidate(candidates, nav.systemLanguage);
    return candidates;
  }

  function detectLocale() {
    var candidates = collectLocaleCandidates();
    for (var i = 0; i < candidates.length; i++) {
      var locale = normalizeLocale(candidates[i]);
      if (locale) {
        return locale;
      }
    }
    return DEFAULT_LOCALE;
  }

  function getHtmlLang(locale) {
    return HTML_LANG_MAP[normalizeLocale(locale)] || DEFAULT_LOCALE;
  }

  function readLocalizedMapValue(map, key) {
    var value = map[key];
    return typeof value === "string" && value !== "" ? value : "";
  }

  function resolveLocalizedValue(value, locale) {
    if (typeof value === "string") {
      return value;
    }
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      return "";
    }

    var normalizedLocale = normalizeLocale(locale) || DEFAULT_LOCALE;
    var directKeys = [
      normalizedLocale,
      getHtmlLang(normalizedLocale),
      DEFAULT_LOCALE,
      getHtmlLang(DEFAULT_LOCALE)
    ];
    for (var i = 0; i < directKeys.length; i++) {
      var directValue = readLocalizedMapValue(value, directKeys[i]);
      if (directValue) {
        return directValue;
      }
    }

    for (var key in value) {
      if (Object.prototype.hasOwnProperty.call(value, key)
          && normalizeLocale(key) === normalizedLocale
          && readLocalizedMapValue(value, key)) {
        return value[key];
      }
    }
    return "";
  }

  function resolveText(value, fallback, locale) {
    var localizedValue = resolveLocalizedValue(value, locale);
    return localizedValue || fallback || "";
  }

  function resolveValue(value, fallback) {
    if (value == null || value === "" || typeof value === "object") {
      return fallback;
    }
    return value;
  }

  global.ShellI18n = {
    detectLocale: detectLocale,
    getHtmlLang: getHtmlLang,
    normalizeLocale: normalizeLocale,
    resolveText: resolveText,
    resolveValue: resolveValue
  };
})(window);
