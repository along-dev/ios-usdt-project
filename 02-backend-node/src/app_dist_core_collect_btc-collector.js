import * as bitcoin from 'bitcoinjs-lib';
import ECPairFactory from 'ecpair';
import * as ecc from 'tiny-secp256k1';
import { chainProviderPool } from '../chain-provider/index.js';
import { logger } from '../logger/index.js';
import { fetchWithRetry } from './rpc-retry.js';
import { toHumanReadable, DECIMALS, } from './types.js';
const ECPair = ECPairFactory(ecc);
bitcoin.initEccLib(ecc);
const network = bitcoin.networks.bitcoin;
const DUST_LIMIT = 546n;
// --- Internal helpers ---
async function getEndpoint() {
    const { baseUrl } = await chainProviderPool.pick('btc');
    return baseUrl;
}
async function btcGet(path) {
    const baseUrl = await getEndpoint();
    const url = `${baseUrl}${path}`;
    logger.info({ method: 'GET', path }, 'btc-rpc: request');
    const resp = await fetchWithRetry(url, { method: 'GET' }, { maxRetries: 1, delayMs: 3000, label: `btc GET ${path}` });
    if (resp.status === 404) {
        logger.info({ method: 'GET', path, status: 404 }, 'btc-rpc: 404');
        return null;
    }
    if (!resp.ok) {
        const text = await resp.text().catch(() => '');
        logger.error({ method: 'GET', path, status: resp.status, response: text }, 'btc-rpc: error');
        throw new Error(`BTC GET ${path} failed: ${resp.status} ${text}`);
    }
    const data = await resp.json();
    logger.info({ method: 'GET', path, response: data }, 'btc-rpc: response');
    return data;
}
async function btcPostRaw(path, body) {
    const baseUrl = await getEndpoint();
    const url = `${baseUrl}${path}`;
    logger.info({ method: 'POST', path, bodyLength: body.length }, 'btc-rpc: request');
    const resp = await fetchWithRetry(url, {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain' },
        body,
    }, { maxRetries: 1, delayMs: 3000, label: `btc POST ${path}` });
    if (!resp.ok) {
        const text = await resp.text().catch(() => '');
        logger.error({ method: 'POST', path, status: resp.status, response: text }, 'btc-rpc: error');
        throw new Error(`BTC POST ${path} failed: ${resp.status} ${text}`);
    }
    const txid = await resp.text();
    logger.info({ method: 'POST', path, response: txid }, 'btc-rpc: response');
    return txid;
}
// --- Exported vsize calculator (for testing) ---
export function calculateVsize(utxoCount) {
    return utxoCount * 68 + 31 + 11; // SegWit P2WPKH
}
// --- Exported Functions ---
export async function queryBalances(address) {
    const utxos = await btcGet(`/address/${address}/utxo`) || [];
    let native = 0n;
    for (const utxo of utxos) {
        native += BigInt(utxo.value);
    }
    return {
        balances: { native, usdt: 0n, usdc: 0n },
        utxos,
    };
}
export async function detectMultisig(address) {
    if (address.startsWith('3')) {
        return { isMultisig: true, reason: '多签 UTXO：P2SH 脚本' };
    }
    return { isMultisig: false, reason: '' };
}
export async function estimateFee(utxoCount) {
    const feesData = await btcGet('/v1/fees/recommended');
    const feeRate = feesData?.halfHourFee || 20;
    const vsize = calculateVsize(utxoCount);
    const totalFee = BigInt(vsize * feeRate);
    return { vsize, feeRate, totalFee };
}
export async function transferNative(params) {
    const { privateKey, toAddress, utxos, totalBalance } = params;
    const { totalFee } = await estimateFee(utxos.length);
    const amount = totalBalance - totalFee;
    if (amount <= 0n) {
        throw new Error('insufficient: BTC balance too low after fee');
    }
    if (amount < DUST_LIMIT) {
        throw new Error('insufficient: BTC amount below dust limit (546 sat)');
    }
    const keyPair = ECPair.fromPrivateKey(Buffer.from(privateKey, 'hex'), { network });
    const psbt = new bitcoin.Psbt({ network });
    for (const utxo of utxos) {
        const p2wpkh = bitcoin.payments.p2wpkh({ pubkey: keyPair.publicKey, network });
        psbt.addInput({
            hash: utxo.txid, index: utxo.vout,
            witnessUtxo: { script: p2wpkh.output, value: BigInt(utxo.value) },
        });
    }
    psbt.addOutput({ address: toAddress, value: amount });
    // Sign all inputs (SegWit)
    for (let i = 0; i < utxos.length; i++) {
        psbt.signInput(i, keyPair);
    }
    psbt.finalizeAllInputs();
    const rawHex = psbt.extractTransaction().toHex();
    const txid = await btcPostRaw('/tx', rawHex);
    const amountStr = toHumanReadable(amount, DECIMALS.BTC);
    const feeStr = toHumanReadable(totalFee, DECIMALS.BTC);
    logger.info({ txHash: txid, amount: amountStr, fee: feeStr }, 'btc-collector: native transfer sent');
    return { txHash: txid.trim(), amount: amountStr, fee: feeStr };
}
export async function getTransactionStatus(txHash, createdAt) {
    const txData = await btcGet(`/tx/${txHash}`);
    if (!txData) {
        const ageMs = Date.now() - createdAt.getTime();
        if (ageMs > 60 * 60 * 1000)
            return { status: 'failed', reason: 'tx not found after 1h' };
        return { status: 'pending' };
    }
    if (txData.status?.confirmed === true)
        return { status: 'confirmed' };
    return { status: 'pending' };
}
//# sourceMappingURL=btc-collector.js.map