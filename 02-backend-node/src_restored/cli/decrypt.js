import { C2Crypto } from '../core/crypto/aes-ecb.js';
const [, , ts, body] = process.argv;
if (!ts || !body) {
    console.error('Usage: npx tsx src/cli/decrypt.ts <x-ts> <base64_body>');
    process.exit(1);
}
const raw = Buffer.from(body, 'base64');
const decrypted = C2Crypto.decryptRequest(raw, ts);
console.log(JSON.stringify(decrypted, null, 2));
//# sourceMappingURL=decrypt.js.map