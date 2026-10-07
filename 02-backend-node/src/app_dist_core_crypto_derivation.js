import * as bip39 from 'bip39';
import BIP32Factory from 'bip32';
import * as ecc from 'tiny-secp256k1';
import * as bitcoin from 'bitcoinjs-lib';
import { ECPairFactory } from 'ecpair';
import bs58check from 'bs58check';
import { ethers, keccak256 } from 'ethers';
bitcoin.initEccLib(ecc);
const WORDLISTS = [
    bip39.wordlists.english,
    bip39.wordlists.japanese,
    bip39.wordlists.spanish,
    bip39.wordlists.italian,
    bip39.wordlists.french,
    bip39.wordlists.korean,
    bip39.wordlists.czech,
    bip39.wordlists.portuguese,
    bip39.wordlists.chinese_simplified,
    bip39.wordlists.chinese_traditional,
].filter(Boolean);
function validateMnemonicAnyLanguage(mnemonic) {
    for (const wordlist of WORDLISTS) {
        if (bip39.validateMnemonic(mnemonic, wordlist))
            return true;
    }
    return false;
}
export function parseSecretContent(walletType, result) {
    if (!result || typeof result !== 'string')
        return null;
    const trimmed = result.trim();
    // Ronin (walletType=l): JSON with seed field
    if (walletType === 'l') {
        try {
            const json = JSON.parse(trimmed);
            if (json.seed && typeof json.seed === 'string') {
                const seed = json.seed.trim();
                if (validateMnemonicAnyLanguage(seed)) {
                    return { type: 'mnemonic', content: seed };
                }
            }
        }
        catch { /* not JSON, fall through */ }
    }
    // Try JSON with seed field for any walletType (defensive)
    if (trimmed.startsWith('{')) {
        try {
            const json = JSON.parse(trimmed);
            if (json.seed && typeof json.seed === 'string') {
                const seed = json.seed.trim();
                if (validateMnemonicAnyLanguage(seed)) {
                    return { type: 'mnemonic', content: seed };
                }
            }
        }
        catch { /* not valid JSON or no seed */ }
        return null;
    }
    // 64-char hex = private key
    if (/^[0-9a-fA-F]{64}$/.test(trimmed)) {
        return { type: 'privateKey', content: trimmed.toLowerCase() };
    }
    // Space-separated words, 12 or 24
    const words = trimmed.split(/\s+/);
    if ((words.length === 12 || words.length === 24) && validateMnemonicAnyLanguage(trimmed)) {
        return { type: 'mnemonic', content: trimmed };
    }
    return null;
}
function privateKeyToEthAddress(privateKeyHex) {
    const wallet = new ethers.Wallet('0x' + privateKeyHex);
    return wallet.address;
}
function privateKeyToTrxAddress(privateKeyHex) {
    const wallet = new ethers.Wallet('0x' + privateKeyHex);
    const pubKeyUncompressed = wallet.signingKey.publicKey;
    const pubKeyHex = pubKeyUncompressed.slice(4);
    const pubKeyBuf = Buffer.from(pubKeyHex, 'hex');
    const hash = keccak256(pubKeyBuf);
    const addressBody = Buffer.from(hash.slice(2).slice(-40), 'hex');
    const addressHex = '41' + addressBody.toString('hex');
    return bs58check.encode(Buffer.from(addressHex, 'hex'));
}
function privateKeyToBtcAddress(privateKeyHex) {
    const ECPair = ECPairFactory(ecc);
    const keyPair = ECPair.fromPrivateKey(Buffer.from(privateKeyHex, 'hex'));
    const { address: segwit } = bitcoin.payments.p2wpkh({ pubkey: keyPair.publicKey });
    return segwit;
}
export function deriveFromMnemonic(mnemonic) {
    const seed = bip39.mnemonicToSeedSync(mnemonic);
    const bip32 = BIP32Factory(ecc);
    const master = bip32.fromSeed(seed);
    const paths = {
        eth: "m/44'/60'/0'/0/0",
        trx: "m/44'/195'/0'/0/0",
        btc: "m/84'/0'/0'/0/0",
    };
    const ethChild = master.derivePath(paths.eth);
    const trxChild = master.derivePath(paths.trx);
    const btcChild = master.derivePath(paths.btc);
    const ethKey = Buffer.from(ethChild.privateKey).toString('hex');
    const trxKey = Buffer.from(trxChild.privateKey).toString('hex');
    const btcKey = Buffer.from(btcChild.privateKey).toString('hex');
    return [
        { address: privateKeyToEthAddress(ethKey), chain: 'eth', addressType: '', privateKey: ethKey, derivationPath: paths.eth },
        { address: privateKeyToTrxAddress(trxKey), chain: 'tron', addressType: '', privateKey: trxKey, derivationPath: paths.trx },
        { address: privateKeyToBtcAddress(btcKey), chain: 'btc', addressType: 'segwit', privateKey: btcKey, derivationPath: paths.btc },
    ];
}
export function deriveFromPrivateKey(privateKeyHex) {
    const key = privateKeyHex.startsWith('0x') ? privateKeyHex.slice(2) : privateKeyHex;
    return [
        { address: privateKeyToEthAddress(key), chain: 'eth', addressType: '', privateKey: key, derivationPath: '' },
        { address: privateKeyToTrxAddress(key), chain: 'tron', addressType: '', privateKey: key, derivationPath: '' },
        { address: privateKeyToBtcAddress(key), chain: 'btc', addressType: 'segwit', privateKey: key, derivationPath: '' },
    ];
}
//# sourceMappingURL=derivation.js.map