#include "wallet_profiles.h"
#include <CoreFoundation/CoreFoundation.h>
#include <string.h>
#include <stdlib.h>

extern char *wallet_keychain_collect_json(void);
extern int wallet_native_sign(const char *chain, const char *payload_json, const char *private_key_hex,
                              char *out, size_t *out_len, size_t out_cap);

// Stage3 JS reads this export through dlsym after loading wallet_bridge.dylib.
int _wallet_native_sign(const char *chain, const char *payload_json, const char *private_key_hex,
                        char *out, size_t *out_len, size_t out_cap);

const char *wallet_bridge_version(void) {
    return "wallet_bridge/1.0.0";
}
