export const UNKNOWN_SOURCE_DOMAIN = '__unknown__';
export const DATA_TYPE_LABELS = {
    whatsapp: 'WS',
    telegram: 'TG',
    mnemonic: '助记词',
};
export const COLLECT_KEYS = [
    'eth_native',
    'eth_usdt',
    'eth_usdc',
    'tron_native',
    'tron_usdt',
    'btc_native',
];
export const COLLECT_KEY_SET = new Set(COLLECT_KEYS);
export const COLLECT_LABELS = {
    eth_native: 'ETH',
    eth_usdt: 'USDT(ETH)',
    eth_usdc: 'USDC(ETH)',
    tron_native: 'TRX',
    tron_usdt: 'USDT(TRON)',
    btc_native: 'BTC',
};
export const VISIBLE_COLLECT_KEYS_BY_CHAIN = {
    eth: ['eth_native', 'eth_usdt', 'eth_usdc'],
    tron: ['tron_native', 'tron_usdt'],
    btc: ['btc_native'],
};
export function normalizeSourceDomain(value) {
    const trimmed = typeof value === 'string' ? value.trim() : '';
    return trimmed || UNKNOWN_SOURCE_DOMAIN;
}
//# sourceMappingURL=constants.js.map