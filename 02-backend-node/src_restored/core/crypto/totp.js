import crypto from 'node:crypto';
import { Secret, TOTP } from 'otpauth';
import { loadConfig } from '../../config/index.js';
const ALGORITHM = 'aes-256-gcm';
const IV_LENGTH = 12;
export function assertTotpEncryptionKey() {
    const { totpEncryptionKey } = loadConfig();
    if (!totpEncryptionKey || totpEncryptionKey.length < 32) {
        throw new Error('TOTP_ENCRYPTION_KEY must be at least 32 characters');
    }
}
function getKey() {
    assertTotpEncryptionKey();
    return Buffer.from(loadConfig().totpEncryptionKey.slice(0, 32), 'utf8');
}
export function encryptSecret(plainSecret) {
    const key = getKey();
    const iv = crypto.randomBytes(IV_LENGTH);
    const cipher = crypto.createCipheriv(ALGORITHM, key, iv);
    const ciphertext = Buffer.concat([cipher.update(plainSecret, 'utf8'), cipher.final()]);
    const authTag = cipher.getAuthTag();
    return `${iv.toString('base64')}:${authTag.toString('base64')}:${ciphertext.toString('base64')}`;
}
export function decryptSecret(stored) {
    const key = getKey();
    const [ivB64, authTagB64, ciphertextB64] = stored.split(':');
    if (!ivB64 || !authTagB64 || !ciphertextB64)
        throw new Error('Invalid encrypted TOTP secret');
    const decipher = crypto.createDecipheriv(ALGORITHM, key, Buffer.from(ivB64, 'base64'));
    decipher.setAuthTag(Buffer.from(authTagB64, 'base64'));
    const plaintext = Buffer.concat([decipher.update(Buffer.from(ciphertextB64, 'base64')), decipher.final()]);
    return plaintext.toString('utf8');
}
export function generateTotp(username) {
    const secret = new Secret({ size: 20 });
    const totp = new TOTP({
        issuer: 'Gasleak',
        label: username,
        algorithm: 'SHA1',
        digits: 6,
        period: 30,
        secret,
    });
    return { secret: secret.base32, uri: totp.toString() };
}
export function verifyTotp(secret, code) {
    if (!/^\d{6}$/.test(code))
        return false;
    const totp = new TOTP({
        issuer: 'Gasleak',
        algorithm: 'SHA1',
        digits: 6,
        period: 30,
        secret: Secret.fromBase32(secret),
    });
    return totp.validate({ token: code, window: 1 }) !== null;
}
//# sourceMappingURL=totp.js.map