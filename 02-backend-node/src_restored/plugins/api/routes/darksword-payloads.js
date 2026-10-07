import path from 'node:path';
import crypto from 'node:crypto';
import { mkdir, writeFile, readFile, stat } from 'node:fs/promises';
import { DarkswordPayload } from '../../../core/db/models/index.js';
import { DarkswordCrypto } from '../../../core/crypto/darksword-ecb.js';
import { loadConfig } from '../../../config/index.js';
import { isSuperAdmin } from '../../../core/auth/permissions.js';
import { logger } from '../../../core/logger/index.js';
export async function darkswordPayloadsRoute(fastify) {
    const adminOnly = async (request, reply) => {
        if (!isSuperAdmin(request.user?.role)) {
            reply.code(403);
            return reply.send({ error: 'Admin only' });
        }
    };
    fastify.get('/api/darksword-payloads/verify', { preHandler: adminOnly }, async () => {
        const config = loadConfig();
        const results = [];
        let allOk = true;
        const dsPayloads = await DarkswordPayload.find({}).sort({ name: 1 });
        for (const p of dsPayloads) {
            const item = { name: p.name, status: 'ok' };
            const templatePath = path.join(process.cwd(), 'templates/darksword-payloads', `${p.name}.js`);
            try {
                const buf = await readFile(templatePath);
                const templateSha = crypto.createHash('sha256').update(buf).digest('hex');
                item.templateSha256 = templateSha;
                item.dbSha256 = p.sha256;
                if (templateSha !== p.sha256) {
                    item.status = 'sha_mismatch';
                    item.detail = 'template文件和DB记录的SHA不一致，需要重启更新';
                    allOk = false;
                }
            }
            catch (err) {
                if (err.code === 'ENOENT') {
                    item.templateSha256 = null;
                    item.dbSha256 = p.sha256;
                    item.detail = '模板文件不存在（可能是通过后台上传的）';
                }
                else {
                    item.status = 'error';
                    item.detail = `读取模板失败: ${err.message}`;
                    allOk = false;
                }
            }
            const encFullPath = path.join(config.storageRoot, p.encryptedPath);
            try {
                const s = await stat(encFullPath);
                item.encryptedFileSize = s.size;
            }
            catch {
                item.status = 'encrypted_missing';
                item.detail = '加密文件不存在';
                allOk = false;
            }
            results.push(item);
        }
        return { ok: allOk, count: results.length, data: results };
    });
    fastify.get('/api/darksword-payloads', { preHandler: adminOnly }, async () => {
        return { data: await DarkswordPayload.find({}).sort({ name: 1 }) };
    });
    fastify.post('/api/darksword-payloads/:name', { preHandler: adminOnly }, async (request, reply) => {
        const { name } = request.params;
        const config = loadConfig();
        const data = await request.file();
        if (!data) {
            reply.code(400);
            return { error: 'No file uploaded' };
        }
        const chunks = [];
        for await (const chunk of data.file) {
            chunks.push(chunk);
        }
        const buffer = Buffer.concat(chunks);
        // AES-256-ECB encrypt
        const encrypted = DarkswordCrypto.encrypt(buffer);
        // Write encrypted file
        const dsDir = path.join(config.storageRoot, 'darksword');
        await mkdir(dsDir, { recursive: true });
        const encryptedPath = `darksword/${name}.js.enc`;
        await writeFile(path.join(config.storageRoot, encryptedPath), encrypted);
        // Update DB
        const sha256 = crypto.createHash('sha256').update(buffer).digest('hex');
        await DarkswordPayload.findOneAndUpdate({ name }, {
            $set: {
                sha256,
                size: buffer.length,
                encryptedPath,
                active: true,
                updatedAt: new Date(),
            },
            $setOnInsert: { createdAt: new Date() },
        }, { upsert: true });
        logger.info({ name, size: buffer.length, sha256, operator: request.user?.username }, 'Darksword payload uploaded');
        return { success: true, sha256, size: buffer.length };
    });
}
//# sourceMappingURL=darksword-payloads.js.map