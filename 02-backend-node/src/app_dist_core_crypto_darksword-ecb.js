import crypto from 'node:crypto';
import { C2_CONSTANTS } from '../../config/constants.js';
export class DarkswordCrypto {
    static encrypt(plaintext) {
        const key = Buffer.from(C2_CONSTANTS.DARKSWORD_PAYLOAD_KEY, 'hex');
        const cipher = crypto.createCipheriv('aes-256-ecb', key, null);
        return Buffer.concat([cipher.update(plaintext), cipher.final()]);
    }
}
//# sourceMappingURL=darksword-ecb.js.map