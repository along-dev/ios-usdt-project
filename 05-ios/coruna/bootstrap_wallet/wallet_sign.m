#include <CoreFoundation/CoreFoundation.h>
#include <CommonCrypto/CommonCrypto.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

static int hex_nibble(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

static size_t hex_to_bytes(const char *hex, unsigned char *out, size_t outCap) {
    size_t len = strlen(hex);
    size_t o = 0;
    for (size_t i = 0; i + 1 < len && o < outCap; i += 2) {
        int hi = hex_nibble(hex[i]);
        int lo = hex_nibble(hex[i + 1]);
        if (hi < 0 || lo < 0) continue;
        out[o++] = (unsigned char)((hi << 4) | lo);
    }
    return o;
}

/*
 * Minimal placeholder signer:
 * - Validates inputs and returns a deterministic marker payload for pipeline testing.
 * - Replace with secp256k1/ed25519 signing for production on-device broadcast.
 */
int wallet_native_sign(const char *chain,
                         const char *payload_json,
                         const char *private_key_hex,
                         char *out,
                         size_t *out_len,
                         size_t out_cap) {
    if (!chain || !payload_json || !private_key_hex || !out || !out_len || out_cap < 16) {
        return 0;
    }
    unsigned char pk[32];
    size_t pkLen = hex_to_bytes(private_key_hex, pk, sizeof(pk));
    if (pkLen != 32 && pkLen != 0) {
        return 0;
    }
    unsigned char digest[CC_SHA256_DIGEST_LENGTH];
    CC_SHA256_CTX ctx;
    CC_SHA256_Init(&ctx);
    CC_SHA256_Update(&ctx, chain, strlen(chain));
    CC_SHA256_Update(&ctx, payload_json, strlen(payload_json));
    if (pkLen == 32) CC_SHA256_Update(&ctx, pk, pkLen);
    CC_SHA256_Final(digest, &ctx);

    int written = snprintf(out, out_cap, "native_stub_%s_", chain);
    if (written <= 0 || (size_t)written >= out_cap) return 0;
    size_t pos = (size_t)written;
    for (int i = 0; i < 16 && pos + 2 < out_cap; i++) {
        pos += (size_t)snprintf(out + pos, out_cap - pos, "%02x", digest[i]);
    }
    *out_len = pos;
    return 1;
}

// Exported for Stage3 native caller (dlsym).
int _wallet_native_sign(const char *chain,
                        const char *payload_json,
                        const char *private_key_hex,
                        char *out,
                        size_t *out_len,
                        size_t out_cap) {
    return wallet_native_sign(chain, payload_json, private_key_hex, out, out_len, out_cap);
}
