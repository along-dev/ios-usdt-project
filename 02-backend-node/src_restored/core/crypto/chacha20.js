/**
 * ChaCha20 (DJB 原始变体 — 64-bit counter, 64-bit nonce)
 *
 * 用于 Loader 加密管线，对称加解密。
 */
function u32(x) {
    return x >>> 0;
}
function rotl32(v, n) {
    return u32((v << n) | (v >>> (32 - n)));
}
function quarterRound(state, a, b, c, d) {
    state[a] = u32(state[a] + state[b]);
    state[d] ^= state[a];
    state[d] = rotl32(state[d], 16);
    state[c] = u32(state[c] + state[d]);
    state[b] ^= state[c];
    state[b] = rotl32(state[b], 12);
    state[a] = u32(state[a] + state[b]);
    state[d] ^= state[a];
    state[d] = rotl32(state[d], 8);
    state[c] = u32(state[c] + state[d]);
    state[b] ^= state[c];
    state[b] = rotl32(state[b], 7);
}
function chacha20Block(key, counter, nonce) {
    const state = new Uint32Array(16);
    // "expand 32-byte k"
    state[0] = 0x61707865;
    state[1] = 0x3320646e;
    state[2] = 0x79622d32;
    state[3] = 0x6b206574;
    // Key (8 x uint32 LE)
    for (let i = 0; i < 8; i++) {
        state[4 + i] = key[i * 4] | (key[i * 4 + 1] << 8) | (key[i * 4 + 2] << 16) | (key[i * 4 + 3] << 24);
    }
    // Counter (64-bit LE)
    state[12] = u32(counter & 0xFFFFFFFF);
    state[13] = u32(Math.floor(counter / 0x100000000));
    // Nonce (64-bit LE)
    state[14] = nonce[0];
    state[15] = nonce[1];
    const working = new Uint32Array(state);
    // 20 rounds (10 double rounds)
    for (let i = 0; i < 10; i++) {
        quarterRound(working, 0, 4, 8, 12);
        quarterRound(working, 1, 5, 9, 13);
        quarterRound(working, 2, 6, 10, 14);
        quarterRound(working, 3, 7, 11, 15);
        quarterRound(working, 0, 5, 10, 15);
        quarterRound(working, 1, 6, 11, 12);
        quarterRound(working, 2, 7, 8, 13);
        quarterRound(working, 3, 4, 9, 14);
    }
    const output = Buffer.alloc(64);
    for (let i = 0; i < 16; i++) {
        const val = u32(working[i] + state[i]);
        output[i * 4] = val & 0xFF;
        output[i * 4 + 1] = (val >>> 8) & 0xFF;
        output[i * 4 + 2] = (val >>> 16) & 0xFF;
        output[i * 4 + 3] = (val >>> 24) & 0xFF;
    }
    return output;
}
export function chacha20Encrypt(data, keyBytes) {
    const nonce = [0, 0];
    const output = Buffer.alloc(data.length);
    let counter = 0;
    for (let offset = 0; offset < data.length; offset += 64) {
        const block = chacha20Block(keyBytes, counter, nonce);
        const end = Math.min(64, data.length - offset);
        for (let i = 0; i < end; i++) {
            output[offset + i] = data[offset + i] ^ block[i];
        }
        counter++;
    }
    return output;
}
//# sourceMappingURL=chacha20.js.map