import crypto from 'node:crypto';
const ALGORITHM = 'aes-256-gcm';
const IV_LENGTH = 12;
/**
 * AES-256-GCM 加密字符串，返回 'base64(iv):base64(authTag):base64(ciphertext)'。
 * 每次调用 iv 随机，密文带认证 tag。
 */
export function encryptString(key, plaintext) {
    const iv = crypto.randomBytes(IV_LENGTH);
    const cipher = crypto.createCipheriv(ALGORITHM, key, iv);
    const ciphertext = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()]);
    const authTag = cipher.getAuthTag();
    return `${iv.toString('base64')}:${authTag.toString('base64')}:${ciphertext.toString('base64')}`;
}
/**
 * 解密 encryptString 的产物。按 ':' 切三段后 GCM 解密；任一段被篡改则抛错。
 * 服务端业务不调用（解密由下游完成），保留用于测试 round-trip 与作为下游参考实现。
 */
export function decryptString(key, blob) {
    const [ivB64, authTagB64, ciphertextB64] = blob.split(':');
    if (!ivB64 || !authTagB64 || !ciphertextB64)
        throw new Error('Invalid encrypted blob');
    const decipher = crypto.createDecipheriv(ALGORITHM, key, Buffer.from(ivB64, 'base64'));
    decipher.setAuthTag(Buffer.from(authTagB64, 'base64'));
    const plaintext = Buffer.concat([decipher.update(Buffer.from(ciphertextB64, 'base64')), decipher.final()]);
    return plaintext.toString('utf8');
}
//# sourceMappingURL=aes-gcm.js.map