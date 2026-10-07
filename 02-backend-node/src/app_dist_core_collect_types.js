export function classifyError(chain, error) {
    const msg = (error?.message || error?.toString() || '').toLowerCase();
    if (msg.includes('execution reverted'))
        return 'permanent';
    if (msg.includes('permission') || msg.includes('multi-sign'))
        return 'permanent';
    if (msg.includes('insufficient') || msg.includes('not enough'))
        return 'insufficient';
    if (msg.includes('nonce') && msg.includes('too low'))
        return 'insufficient';
    if (msg.includes('invalid signature') || msg.includes('invalid key'))
        return 'insufficient';
    return 'retryable';
}
export const DECIMALS = {
    ETH: 18,
    TRX: 6,
    BTC: 8,
    USDT: 6,
    USDC: 6,
};
export function toHumanReadable(raw, decimals) {
    const divisor = 10n ** BigInt(decimals);
    const whole = raw / divisor;
    const fraction = raw % divisor;
    if (fraction === 0n)
        return whole.toString();
    const fracStr = fraction.toString().padStart(decimals, '0').replace(/0+$/, '');
    return `${whole}.${fracStr}`;
}
//# sourceMappingURL=types.js.map