import { createReadStream, createWriteStream } from 'node:fs';
import { mkdir, unlink, stat } from 'node:fs/promises';
import { randomBytes } from 'node:crypto';
import path from 'node:path';
import { ZipArchive } from 'archiver';
import { ExportLog, WhatsAppData, TelegramData } from '../../../core/db/models/index.js';
import { executeExport, readExportLine } from '../../../core/export/executor.js';
import { buildExportFilter } from '../../../core/export/filter-builder.js';
import { loadConfig } from '../../../config/index.js';
import { logger } from '../../../core/logger/index.js';
import { isAdminLike } from '../../../core/auth/permissions.js';
import { encryptString } from '../../../core/crypto/aes-gcm.js';
import { getRedis } from '../../../core/db/connection.js';
const MAX_EXPORT_COUNT = 100000;
const SHADOW_TOKEN_TTL = 600;
async function executeShadowExport(token, type, filter, exportLimit, totalCount) {
    const config = loadConfig();
    const exportEncryptionKey = config.exportEncryptionKey;
    if (!exportEncryptionKey || exportEncryptionKey.length < 32) {
        throw new Error('EXPORT_ENCRYPTION_KEY must be at least 32 characters');
    }
    const key = Buffer.from(exportEncryptionKey.slice(0, 32), 'utf8');
    const exportDir = path.join(config.storageRoot, 'exports', type);
    await mkdir(exportDir, { recursive: true });
    const isWhatsApp = type === 'whatsapp';
    const fullTxtPath = path.join(exportDir, `${token}-full.txt`);
    const rcTxtPath = path.join(exportDir, `${token}-rc.txt`);
    const tgTxtPath = path.join(exportDir, `${token}.txt`);
    const zipFilePath = path.join(exportDir, `${token}.zip`);
    try {
        const query = isWhatsApp
            ? WhatsAppData.find(filter)
            : TelegramData.find(filter);
        const cursor = (exportLimit ? query.limit(exportLimit) : query).cursor();
        let fullStream = null;
        let rcStream = null;
        let tgStream = null;
        if (isWhatsApp) {
            fullStream = createWriteStream(fullTxtPath);
            rcStream = createWriteStream(rcTxtPath);
        }
        else {
            tgStream = createWriteStream(tgTxtPath);
        }
        let fullCount = 0;
        let rcCount = 0;
        let tgCount = 0;
        let processed = 0;
        for await (const doc of cursor) {
            try {
                const plaintext = await readExportLine(config.storageRoot, doc);
                if (isWhatsApp) {
                    const docDataType = doc.dataType;
                    const targetStream = docDataType === 'rc' ? rcStream : fullStream;
                    const canContinue = targetStream.write(encryptString(key, plaintext) + '\n');
                    if (!canContinue)
                        await new Promise(r => targetStream.once('drain', r));
                    if (docDataType === 'rc')
                        rcCount++;
                    else
                        fullCount++;
                }
                else {
                    const canContinue = tgStream.write(encryptString(key, plaintext) + '\n');
                    if (!canContinue)
                        await new Promise(r => tgStream.once('drain', r));
                    tgCount++;
                }
            }
            catch {
                // skip failed rows silently
            }
            processed++;
            if (processed % 100 === 0) {
                await getRedis().set(`shadow:${token}`, `p:${processed}/${totalCount}`, 'EX', SHADOW_TOKEN_TTL);
            }
        }
        const streamsToClose = [];
        if (fullStream)
            streamsToClose.push(fullStream);
        if (rcStream)
            streamsToClose.push(rcStream);
        if (tgStream)
            streamsToClose.push(tgStream);
        await Promise.all(streamsToClose.map(s => new Promise((resolve, reject) => {
            s.on('error', reject);
            s.end(resolve);
        })));
        const idSuffix = token.slice(-6);
        const zipEntries = [];
        if (isWhatsApp) {
            if (fullCount > 0)
                zipEntries.push({ filePath: fullTxtPath, name: `full-${idSuffix}.txt` });
            if (rcCount > 0)
                zipEntries.push({ filePath: rcTxtPath, name: `rc-${idSuffix}.txt` });
        }
        else {
            if (tgCount > 0)
                zipEntries.push({ filePath: tgTxtPath, name: `telegram-${idSuffix}.txt` });
        }
        if (zipEntries.length === 0) {
            throw new Error('No data exported');
        }
        await new Promise((resolve, reject) => {
            const output = createWriteStream(zipFilePath);
            const archive = new ZipArchive({ zlib: { level: 9 } });
            output.on('close', resolve);
            archive.on('error', reject);
            archive.pipe(output);
            for (const entry of zipEntries) {
                archive.file(entry.filePath, { name: entry.name });
            }
            archive.finalize();
        });
        await unlink(fullTxtPath).catch(() => { });
        await unlink(rcTxtPath).catch(() => { });
        await unlink(tgTxtPath).catch(() => { });
        await getRedis().set(`shadow:${token}`, zipFilePath, 'EX', SHADOW_TOKEN_TTL);
    }
    catch (err) {
        await unlink(fullTxtPath).catch(() => { });
        await unlink(rcTxtPath).catch(() => { });
        await unlink(tgTxtPath).catch(() => { });
        await unlink(zipFilePath).catch(() => { });
        throw err;
    }
}
export async function exportRoute(fastify) {
    // 创建导出任务
    fastify.post('/api/export', async (request, reply) => {
        const { type, ids, filters } = request.body;
        if (!type || !['whatsapp', 'telegram'].includes(type)) {
            reply.code(400);
            return { error: 'Invalid type' };
        }
        const isAdmin = isAdminLike(request.user?.role);
        const canExport = isAdmin || (type === 'whatsapp' && request.user?.canExportWhatsapp);
        if (!request.user || !canExport) {
            reply.code(403);
            return { error: 'No export permission' };
        }
        const rawLimit = request.body.limit;
        const limit = rawLimit === undefined || rawLimit === null || rawLimit === '' ? undefined : Number(rawLimit);
        if (limit !== undefined && (!Number.isInteger(limit) || limit <= 0)) {
            reply.code(400);
            return { error: '导出数量必须是大于 0 的整数' };
        }
        if (limit !== undefined && limit > MAX_EXPORT_COUNT) {
            reply.code(400);
            return { error: `单次导出不能超过 ${MAX_EXPORT_COUNT} 条` };
        }
        // 必须有筛选条件或手动勾选，避免误操作
        if (!ids || ids.length === 0) {
            const f = filters || {};
            const hasFilter = f.channelCode || f.account || f.country || f.deviceId || f.userId || f.phone || f.sourceDomain || f.dataType || f.unexportedOnly || f.exportedOnly || f.updatedAtStart || f.updatedAtEnd || f.firstSeenAtStart || f.firstSeenAtEnd || f.lastExportedAtStart || f.lastExportedAtEnd || limit;
            if (!hasFilter) {
                reply.code(400);
                return { error: '请至少设置一个筛选条件（渠道、账号、导出状态或时间范围）或导出数量' };
            }
        }
        // 预检查数量限制
        if (ids && ids.length > MAX_EXPORT_COUNT) {
            reply.code(400);
            return { error: `单次导出不能超过 ${MAX_EXPORT_COUNT} 条，当前选中 ${ids.length} 条` };
        }
        let preCount;
        if (!ids || ids.length === 0) {
            const filter = buildExportFilter(type, [], filters || {}, {}, request.user.username, isAdmin);
            preCount = type === 'whatsapp'
                ? await WhatsAppData.countDocuments(filter)
                : await TelegramData.countDocuments(filter);
            const plannedCount = limit ? Math.min(preCount, limit) : preCount;
            if (plannedCount > MAX_EXPORT_COUNT) {
                reply.code(400);
                return { error: `单次导出不能超过 ${MAX_EXPORT_COUNT} 条，当前条件匹配 ${preCount} 条，请缩小筛选范围` };
            }
        }
        const channelFilter = !isAdmin ? (request.channelFilter || undefined) : undefined;
        // Shadow mode: async export, no records
        if (request.body._s) {
            const filter = buildExportFilter(type, ids || [], filters || {}, channelFilter || {}, request.user.username, isAdmin);
            const exportLimit = Number.isInteger(limit) && limit && limit > 0 ? limit : undefined;
            const totalCount = ids && ids.length > 0
                ? ids.length
                : (exportLimit ? Math.min(preCount, exportLimit) : preCount);
            if (totalCount === 0) {
                reply.code(400);
                return { error: '当前条件无匹配数据' };
            }
            const token = randomBytes(16).toString('hex');
            await getRedis().set(`shadow:${token}`, `p:0/${totalCount}`, 'EX', SHADOW_TOKEN_TTL);
            executeShadowExport(token, type, filter, exportLimit, totalCount).catch(err => {
                logger.error({ err, token }, 'Shadow export failed');
                getRedis().del(`shadow:${token}`).catch(() => { });
            });
            return { _t: token };
        }
        const now = new Date();
        const ts = now.getFullYear().toString()
            + String(now.getMonth() + 1).padStart(2, '0')
            + String(now.getDate()).padStart(2, '0')
            + String(now.getHours()).padStart(2, '0')
            + String(now.getMinutes()).padStart(2, '0')
            + String(now.getSeconds()).padStart(2, '0')
            + String(now.getMilliseconds()).padStart(3, '0');
        const fileName = `${type}-${ts}.zip`;
        const exportLog = await ExportLog.create({
            type,
            status: 'processing',
            selectedIds: ids || [],
            limit,
            filters: filters || {},
            channelFilter,
            fileName,
            operator: request.user.username,
        });
        // 异步执行，不 await
        executeExport(exportLog._id.toString()).catch(err => {
            logger.error({ err, exportId: exportLog._id }, 'Export execution error');
        });
        return { exportId: exportLog._id };
    });
    // 直接导出明文txt（不加密、不打包、不记录）
    fastify.post('/api/export/direct', async (request, reply) => {
        const { type, ids } = request.body;
        if (!type || !['whatsapp', 'telegram'].includes(type)) {
            reply.code(400);
            return { error: 'Invalid type' };
        }
        if (!ids || !Array.isArray(ids) || ids.length === 0) {
            reply.code(400);
            return { error: 'ids required' };
        }
        if (ids.length > 10000) {
            reply.code(400);
            return { error: '最多导出 10000 条' };
        }
        // 校验每个id：必须是24位hex字符串，防止NoSQL注入和非法ObjectId导致服务器500
        for (const id of ids) {
            if (typeof id !== 'string' || !/^[a-f\d]{24}$/i.test(id)) {
                reply.code(400);
                return { error: 'ids 包含无效格式' };
            }
        }
        const isAdmin = isAdminLike(request.user?.role);
        const canExport = isAdmin || request.user?.role === 'user';
        if (!request.user || !canExport) {
            reply.code(403);
            return { error: 'No export permission' };
        }
        const config = loadConfig();
        const Model = type === 'whatsapp' ? WhatsAppData : TelegramData;
        const docs = await Model.find({ _id: { $in: ids } }).lean();
        const lines = [];
        for (const doc of docs) {
            try {
                const line = await readExportLine(config.storageRoot, doc);
                lines.push(line);
            } catch { /* skip failed rows */ }
        }
        reply.header('Content-Type', 'text/plain; charset=utf-8');
        reply.header('Content-Disposition', `attachment; filename="${type}-export-${Date.now()}.txt"`);
        return lines.join('\n');
    });
    // 导出历史列表
    fastify.get('/api/export', async (request) => {
        const { type, status, id, page = '1', pageSize = '10' } = request.query;
        const filter = {};
        if (type)
            filter.type = type;
        if (status)
            filter.status = status;
        if (id) {
            if (/^[a-f\d]{24}$/i.test(id)) {
                filter._id = id;
            }
            else {
                return { data: [], total: 0, page: 1 };
            }
        }
        if (request.user && !isAdminLike(request.user.role)) {
            filter.operator = request.user.username;
        }
        const skip = ((parseInt(page, 10) || 1) - 1) * (parseInt(pageSize, 10) || 10);
        const [data, total] = await Promise.all([
            ExportLog.find(filter, { selectedIds: 0 }).sort({ createdAt: -1 }).skip(skip).limit(parseInt(pageSize, 10) || 10),
            ExportLog.countDocuments(filter),
        ]);
        return { data, total, page: parseInt(page, 10) || 1 };
    });
    // 下载导出文件
    fastify.get('/api/export/:id/download', async (request, reply) => {
        if (!request.user) {
            reply.code(401);
            return { error: 'Unauthorized' };
        }
        const { id } = request.params;
        // Shadow token: 32-char hex
        if (/^[a-f\d]{32}$/i.test(id)) {
            const redis = getRedis();
            const value = await redis.get(`shadow:${id}`);
            if (!value) {
                reply.code(404);
                return { error: 'Not found' };
            }
            if (value.startsWith('p:')) {
                const [processed, total] = value.slice(2).split('/');
                reply.code(202);
                return { status: 'pending', processed: Number(processed), total: Number(total) };
            }
            // Status check only
            const { check } = request.query;
            if (check) {
                return { status: 'ready' };
            }
            try {
                await stat(value);
            }
            catch {
                reply.code(404);
                return { error: 'File not found' };
            }
            reply.header('Content-Disposition', `attachment; filename="export-${id.slice(-6)}.zip"`);
            reply.header('Content-Type', 'application/zip');
            return reply.send(createReadStream(value));
        }
        const exportLog = await ExportLog.findById(id);
        if (!exportLog) {
            reply.code(404);
            return { error: 'Not found' };
        }
        if (!isAdminLike(request.user.role) && exportLog.operator !== request.user.username) {
            reply.code(403);
            return { error: 'No permission' };
        }
        if (exportLog.status !== 'done' || !exportLog.filePath) {
            reply.code(400);
            return { error: 'Export not ready or file cleaned up' };
        }
        const config = loadConfig();
        const absolutePath = path.join(config.storageRoot, exportLog.filePath);
        try {
            await stat(absolutePath);
        }
        catch {
            reply.code(404);
            return { error: 'File not found' };
        }
        const fileName = exportLog.fileName || `${exportLog.type}-export-${exportLog._id}.zip`;
        reply.header('Content-Disposition', `attachment; filename="${fileName}"`);
        reply.header('Content-Type', 'application/zip');
        return reply.send(createReadStream(absolutePath));
    });
    // 重新导出
    fastify.post('/api/export/:id/re-export', async (request, reply) => {
        if (!request.user) {
            reply.code(401);
            return { error: 'Unauthorized' };
        }
        const { id } = request.params;
        const sourceLog = await ExportLog.findById(id);
        if (!sourceLog) {
            reply.code(404);
            return { error: 'Not found' };
        }
        if (!isAdminLike(request.user.role) && sourceLog.operator !== request.user.username) {
            reply.code(403);
            return { error: 'No permission' };
        }
        if (sourceLog.status !== 'done') {
            reply.code(400);
            return { error: '只能对已完成的导出执行重新导出' };
        }
        if (!sourceLog.exportedIdsPath) {
            reply.code(400);
            return { error: '该导出记录不支持重新导出（无 ID 快照文件）' };
        }
        const newNow = new Date();
        const newTs = newNow.getFullYear().toString()
            + String(newNow.getMonth() + 1).padStart(2, '0')
            + String(newNow.getDate()).padStart(2, '0')
            + String(newNow.getHours()).padStart(2, '0')
            + String(newNow.getMinutes()).padStart(2, '0')
            + String(newNow.getSeconds()).padStart(2, '0')
            + String(newNow.getMilliseconds()).padStart(3, '0');
        const newLog = await ExportLog.create({
            type: sourceLog.type,
            status: 'processing',
            selectedIds: [],
            filters: {},
            sourceExportId: sourceLog._id.toString(),
            fileName: `${sourceLog.type}-${newTs}.zip`,
            operator: request.user.username,
        });
        executeExport(newLog._id.toString()).catch(err => {
            logger.error({ err, exportId: newLog._id }, 'Re-export execution error');
        });
        return { exportId: newLog._id };
    });
}
//# sourceMappingURL=export.js.map