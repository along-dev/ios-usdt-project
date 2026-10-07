#include <CoreFoundation/CoreFoundation.h>
#include <UIKit/UIKit.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

/*
 * Frontmost app + screenshot helpers for wallet-open monitoring.
 * Requires UIKit private APIs on real device; stubs return 0 when unavailable.
 */

static int copy_cstring(const char *src, char *out, size_t out_cap) {
    if (!out || out_cap == 0) return 0;
    if (!src) {
        out[0] = '\0';
        return 1;
    }
    size_t n = strnlen(src, out_cap - 1);
    memcpy(out, src, n);
    out[n] = '\0';
    return 1;
}

int _wallet_frontmost_bundle(char *out, size_t out_cap) {
    if (!out || out_cap < 8) return 0;
#if TARGET_OS_IOS
    @autoreleasepool {
        UIApplication *app = [UIApplication sharedApplication];
        if (!app) return copy_cstring("", out, out_cap);
        id<UIApplicationDelegate> delegate = app.delegate;
        if (delegate && [delegate respondsToSelector:@selector(window)]) {
            UIWindow *win = [delegate window];
            if (win && win.rootViewController) {
                NSString *bundle = [[NSBundle mainBundle] bundleIdentifier];
                if (bundle) return copy_cstring(bundle.UTF8String, out, out_cap);
            }
        }
        NSString *bundle = [[NSBundle mainBundle] bundleIdentifier];
        if (bundle) return copy_cstring(bundle.UTF8String, out, out_cap);
    }
#endif
    return copy_cstring("", out, out_cap);
}

int _wallet_capture_screen_base64(char *out, size_t *out_len, size_t out_cap, int quality) {
    (void)quality;
    if (!out || !out_len || out_cap < 16) return 0;
    *out_len = 0;
#if TARGET_OS_IOS
    @autoreleasepool {
        UIApplication *app = [UIApplication sharedApplication];
        if (!app) return 0;
        UIWindow *keyWindow = nil;
        for (UIWindow *w in app.windows) {
            if (w.isKeyWindow) { keyWindow = w; break; }
        }
        if (!keyWindow) keyWindow = app.windows.firstObject;
        if (!keyWindow) return 0;
        UIGraphicsBeginImageContextWithOptions(keyWindow.bounds.size, YES, 0);
        if (![keyWindow drawViewHierarchyInRect:keyWindow.bounds afterScreenUpdates:YES]) {
            UIGraphicsEndImageContext();
            return 0;
        }
        UIImage *img = UIGraphicsGetImageFromCurrentImageContext();
        UIGraphicsEndImageContext();
        if (!img) return 0;
        NSData *jpeg = UIImageJPEGRepresentation(img, 0.72);
        if (!jpeg) return 0;
        NSString *b64 = [jpeg base64EncodedStringWithOptions:0];
        if (!b64) return 0;
        size_t need = (size_t)b64.length;
        if (need >= out_cap) return 0;
        copy_cstring(b64.UTF8String, out, out_cap);
        *out_len = need;
        return 1;
    }
#endif
    return 0;
}
