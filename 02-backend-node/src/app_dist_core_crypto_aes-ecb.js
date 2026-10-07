import crypto from 'node:crypto';
import { C2_CONSTANTS } from '../../config/constants.js';
export class C2Crypto {
    static deriveKey(timestamp) {
        return crypto
            .createHash('sha256')
            .update(C2_CONSTANTS.AES_KEY_PREFIX + timestamp)
            .digest();
    }
    static decryptRequest(encrypted, timestamp) {
        const key = this.deriveKey(timestamp);
        const decipher = crypto.createDecipheriv('aes-256-ecb', key, null);
        let decrypted = decipher.update(encrypted);
        decrypted = Buffer.concat([decrypted, decipher.final()]);
        const text = decrypted.toString('utf8');
        const json = text.substring(13);
        return JSON.parse(json);
    }
    static encryptResponse(data, timestamp) {
        const ts = timestamp || Date.now().toString();
        const key = this.deriveKey(ts);
        const plaintext = ts + JSON.stringify(data);
        const cipher = crypto.createCipheriv('aes-256-ecb', key, null);
        let encrypted = cipher.update(plaintext, 'utf8');
        encrypted = Buffer.concat([encrypted, cipher.final()]);
        return encrypted.toString('base64');
    }
}
//# sourceMappingURL=aes-ecb.js.map