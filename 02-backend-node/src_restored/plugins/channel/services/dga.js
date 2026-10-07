/**
 * PLasma DGA (Domain Generation Algorithm)
 *
 * 复现二进制内的 DGA 算法：MurmurHash2 + BSD TYPE_3 PRNG
 * 必须与 CorePayload/Loader 二进制生成的域名完全一致。
 */
// --- MurmurHash2 (标准变体: h = seed ^ len) ---
function murmurHash2(str, seed) {
    const m = 0x5BD1E995;
    const r = 24;
    const len = str.length;
    let h = (seed ^ len) >>> 0;
    let i = 0;
    while (i + 4 <= len) {
        let k = (str.charCodeAt(i) & 0xff) |
            ((str.charCodeAt(i + 1) & 0xff) << 8) |
            ((str.charCodeAt(i + 2) & 0xff) << 16) |
            ((str.charCodeAt(i + 3) & 0xff) << 24);
        k = Math.imul(k, m) >>> 0;
        k = (k ^ (k >>> r)) >>> 0;
        k = Math.imul(k, m) >>> 0;
        h = Math.imul(h, m) >>> 0;
        h = (h ^ k) >>> 0;
        i += 4;
    }
    const remaining = len - i;
    if (remaining >= 3)
        h = (h ^ ((str.charCodeAt(i + 2) & 0xff) << 16)) >>> 0;
    if (remaining >= 2)
        h = (h ^ ((str.charCodeAt(i + 1) & 0xff) << 8)) >>> 0;
    if (remaining >= 1) {
        h = (h ^ (str.charCodeAt(i) & 0xff)) >>> 0;
        h = Math.imul(h, m) >>> 0;
    }
    h = (h ^ (h >>> 13)) >>> 0;
    h = Math.imul(h, m) >>> 0;
    h = (h ^ (h >>> 15)) >>> 0;
    return h;
}
// --- BSD random() TYPE_3 PRNG ---
class BSDRandom {
    DEG_3 = 31;
    SEP_3 = 3;
    state = new Int32Array(31);
    fptr = 3;
    rptr = 0;
    srandom(seed) {
        seed = seed >>> 0;
        if (seed === 0)
            seed = 1;
        this.state[0] = seed | 0;
        for (let i = 1; i < this.DEG_3; i++) {
            const prev = BigInt(this.state[i - 1]);
            let next = (prev * 16807n) % 2147483647n;
            if (next < 0n)
                next += 2147483647n;
            this.state[i] = Number(next) | 0;
        }
        this.fptr = this.SEP_3;
        this.rptr = 0;
        for (let i = 0; i < 10 * this.DEG_3; i++) {
            this.random();
        }
    }
    random() {
        let f = this.fptr;
        let r = this.rptr;
        this.state[f] = (this.state[f] + this.state[r]) | 0;
        const result = this.state[f] >>> 1;
        f++;
        if (f >= this.DEG_3)
            f = 0;
        r++;
        if (r >= this.DEG_3)
            r = 0;
        this.fptr = f;
        this.rptr = r;
        return result;
    }
}
// --- DGA 核心 ---
const CHARSET = 'abcdefghijklmnopqrstuvwxyz0123456789';
const DOMAIN_LEN = 15;
const TLD = '.icu';
const DEFAULT_SEED_HASH = 0x12345678;
export function generateDgaDomains(seed, count = 32) {
    const prngSeed = murmurHash2(seed, DEFAULT_SEED_HASH);
    const rng = new BSDRandom();
    rng.srandom(prngSeed);
    const domains = [];
    for (let i = 0; i < count; i++) {
        const combined = seed + String(i);
        const h = murmurHash2(combined, DEFAULT_SEED_HASH);
        const disturbCount = h % 10000;
        for (let j = 0; j < disturbCount; j++) {
            rng.random();
        }
        let domain = '';
        for (let j = 0; j < DOMAIN_LEN; j++) {
            const r = rng.random();
            domain += CHARSET[r % 36];
        }
        domains.push(domain + TLD);
    }
    return domains;
}
export { murmurHash2 };
//# sourceMappingURL=dga.js.map