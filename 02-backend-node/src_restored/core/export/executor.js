import { createWriteStream } from 'node:fs';
import { mkdir, unlink, stat, writeFile, readFile } from 'node:fs/promises';
import path from 'node:path';
import { ZipArchive } from 'archiver';
import { WhatsAppData, TelegramData, ExportLog } from '../db/models/index.js';
import { buildExportFilter } from './filter-builder.js';
import { loadConfig } from '../../config/index.js';
import { logger } from '../logger/index.js';
import { readRawDataText } from '../raw-data/store.js';
import { encryptString } from '../crypto/aes-gcm.js';
const BATCH_UPDATE_SIZE = 1000;
const PROGRESS_INTERVAL = 100;
export async function readExportLine(storageRoot, doc) {
    if (!doc.rawDataRef) {
        throw new Error('rawDataRef missing');
    }
    return readRawDataText(storageRoot, doc.rawDataRef);
}
/**
 * 执行导出任务（异步，不 await）
 */
export async function executeExport(exportId) {
    const exportLog = await ExportLog.findById(exportId);
    if (!exportLog) {
        logger.error({ exportId }, 'Export log not found');
        return;
    }
    const config = loadConfig();
    const { type, filters, limit } = exportLog;
    let { selectedIds } = exportLog;
    // 重新导出：通过 sourceExportId 查原始记录的 ids 文件
    if ((!selectedIds || selectedIds.length === 0) && exportLog.sourceExportId) {
        const sourceLog = await ExportLog.findById(exportLog.sourceExportId, { exportedIdsPath: 1 });
        if (!sourceLog?.exportedIdsPath) {
            await ExportLog.updateOne({ _id: exportId }, { status: 'failed', errorMsg: '原始导出记录无 ID 快照文件' });
            return;
        }
        const idsAbsPath = path.join(config.storageRoot, sourceLog.exportedIdsPath);
        const raw = await readFile(idsAbsPath, 'utf8');
        selectedIds = JSON.parse(raw);
    }
    const isAdmin = !exportLog.channelFilter || Object.keys(exportLog.channelFilter).length === 0;
    const filter = buildExportFilter(type, selectedIds, filters || {}, exportLog.channelFilter || {}, exportLog.operator, isAdmin);
    const exportLimit = Number.isInteger(limit) && limit && limit > 0 ? limit : undefined;
    // 导出目录
    const exportDir = path.join(config.storageRoot, 'exports', type);
    await mkdir(exportDir, { recursive: true });
    // 临时文件路径
    const idSuffix = exportId.slice(-6);
    const errorsCsvPath = path.join(exportDir, `${exportId}-errors.csv`);
    const zipFilePath = path.join(exportDir, `${exportId}.zip`);
    // WA 分文件：full + rc；TG 单文件
    const isWhatsApp = type === 'whatsapp';
    const fullTxtPath = path.join(exportDir, `${exportId}-full.txt`);
    const rcTxtPath = path.join(exportDir, `${exportId}-rc.txt`);
    const tgTxtPath = path.join(exportDir, `${exportId}.txt`);
    try {
        // 强制加密：密钥缺失/过短直接失败，不回退明文
        const exportEncryptionKey = config.exportEncryptionKey;
        if (!exportEncryptionKey || exportEncryptionKey.length < 32) {
            throw new Error('EXPORT_ENCRYPTION_KEY must be at least 32 characters');
        }
        const key = Buffer.from(exportEncryptionKey.slice(0, 32), 'utf8');
        // count 总数
        const matchedCount = type === 'whatsapp'
            ? await WhatsAppData.countDocuments(filter)
            : await TelegramData.countDocuments(filter);
        const totalCount = exportLimit ? Math.min(matchedCount, exportLimit) : matchedCount;
        await ExportLog.updateOne({ _id: exportId }, { totalCount });
        if (totalCount === 0) {
            await ExportLog.updateOne({ _id: exportId }, {
                status: 'done',
                totalCount: 0,
                completedAt: new Date(),
            });
            return;
        }
        // 流式读取并写入
        const errorsStream = createWriteStream(errorsCsvPath);
        await writeLine(errorsStream, type === 'whatsapp' ? '_id,account,error' : '_id,userId,error');
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
        const query = type === 'whatsapp'
            ? WhatsAppData.find(filter)
            : TelegramData.find(filter);
        const cursor = (exportLimit ? query.limit(exportLimit) : query).cursor();
        let processedCount = 0;
        let skippedCount = 0;
        let fullCount = 0;
        let rcCount = 0;
        let hasErrors = false;
        const processedIds = [];
        // 提前注册 error 监听，避免遗漏
        let writeError = null;
        if (fullStream)
            fullStream.on('error', (err) => { writeError = err; });
        if (rcStream)
            rcStream.on('error', (err) => { writeError = err; });
        if (tgStream)
            tgStream.on('error', (err) => { writeError = err; });
        errorsStream.on('error', (err) => { writeError = err; });
        for await (const doc of cursor) {
            if (writeError)
                throw writeError;
            processedCount++;
            try {
                if (isWhatsApp) {
                    const docDataType = doc.dataType;
                    if (!docDataType) {
                        throw new Error('dataType missing');
                    }
                    const plaintext = await readExportLine(config.storageRoot, doc);
                    const targetStream = docDataType === 'rc' ? rcStream : fullStream;
                    await writeLine(targetStream, encryptString(key, plaintext));
                    if (docDataType === 'rc')
                        rcCount++;
                    else
                        fullCount++;
                }
                else {
                    const plaintext = await readExportLine(config.storageRoot, doc);
                    await writeLine(tgStream, encryptString(key, plaintext));
                }
                processedIds.push(doc._id.toString());
            }
            catch (err) {
                skippedCount++;
                hasErrors = true;
                const docId = doc._id.toString();
                const identifier = type === 'whatsapp' ? (doc.account || '') : (doc.userId || '');
                const error = err?.message || 'rawData read failed';
                await writeLine(errorsStream, [
                    docId,
                    identifier,
                    error,
                ].map(csvCell).join(','));
                logger.warn({
                    exportId,
                    type,
                    docId,
                    identifier,
                    rawDataRef: doc.rawDataRef || '',
                    error,
                }, 'Export row skipped');
            }
            // 每 PROGRESS_INTERVAL 条更新进度
            if (processedCount % PROGRESS_INTERVAL === 0) {
                await ExportLog.updateOne({ _id: exportId }, { processedCount, skippedCount });
            }
        }
        if (writeError)
            throw writeError;
        // 关闭写入流
        const streamsToClose = [errorsStream];
        if (fullStream)
            streamsToClose.push(fullStream);
        if (rcStream)
            streamsToClose.push(rcStream);
        if (tgStream)
            streamsToClose.push(tgStream);
        await Promise.all(streamsToClose.map(endWriteStream));
        // 用 archiver 压缩
        const zipEntries = [];
        if (isWhatsApp) {
            if (fullCount > 0)
                zipEntries.push({ filePath: fullTxtPath, name: `full-${idSuffix}.txt` });
            if (rcCount > 0)
                zipEntries.push({ filePath: rcTxtPath, name: `rc-${idSuffix}.txt` });
        }
        else {
            zipEntries.push({ filePath: tgTxtPath, name: `telegram-${idSuffix}.txt` });
        }
        if (hasErrors)
            zipEntries.push({ filePath: errorsCsvPath, name: 'errors.csv' });
        await zipFilesList(zipFilePath, zipEntries);
        // 删除临时文件
        await unlink(fullTxtPath).catch(() => { });
        await unlink(rcTxtPath).catch(() => { });
        await unlink(tgTxtPath).catch(() => { });
        await unlink(errorsCsvPath).catch(() => { });
        // 获取 zip 大小
        const zipStat = await stat(zipFilePath);
        // 分批更新数据库记录
        const now = new Date();
        const operator = exportLog.operator;
        for (let i = 0; i < processedIds.length; i += BATCH_UPDATE_SIZE) {
            const batch = processedIds.slice(i, i + BATCH_UPDATE_SIZE);
            const updateFilter = { _id: { $in: batch } };
            const updateOp = {
                $set: { exported: true, lastExportedAt: now, [`exportHistory.${operator}.lastExportedAt`]: now },
                $inc: { exportCount: 1, [`exportHistory.${operator}.exportCount`]: 1 },
            };
            if (type === 'whatsapp') {
                await WhatsAppData.updateMany(updateFilter, updateOp);
            }
            else {
                await TelegramData.updateMany(updateFilter, updateOp);
            }
        }
        // 写入 ids 文件
        const idsFilePath = path.join(exportDir, `${exportId}-ids.json`);
        await writeFile(idsFilePath, JSON.stringify(processedIds));
        const idsRelativePath = path.relative(config.storageRoot, idsFilePath);
        // 最终更新 ExportLog
        const relativePath = path.relative(config.storageRoot, zipFilePath);
        await ExportLog.updateOne({ _id: exportId }, {
            status: 'done',
            processedCount,
            skippedCount,
            filePath: relativePath,
            fileSize: zipStat.size,
            exportedIdsPath: idsRelativePath,
            completedAt: now,
        });
        logger.info({ exportId, type, totalCount, processedCount, skippedCount }, 'Export completed');
    }
    catch (err) {
        logger.error({ err, exportId }, 'Export failed');
        await ExportLog.updateOne({ _id: exportId }, {
            status: 'failed',
            errorMsg: err.message || 'Unknown error',
        });
        // 清理残留文件
        await unlink(fullTxtPath).catch(() => { });
        await unlink(rcTxtPath).catch(() => { });
        await unlink(tgTxtPath).catch(() => { });
        await unlink(errorsCsvPath).catch(() => { });
        await unlink(zipFilePath).catch(() => { });
    }
}
async function writeLine(stream, line) {
    const canContinue = stream.write(line + '\n');
    if (!canContinue) {
        await new Promise(resolve => stream.once('drain', resolve));
    }
}
function endWriteStream(stream) {
    return new Promise((resolve, reject) => {
        stream.on('error', reject);
        stream.end(resolve);
    });
}
function csvCell(value) {
    if (/[",\n\r]/.test(value)) {
        return `"${value.replaceAll('"', '""')}"`;
    }
    return value;
}
/**
 * 将文件列表打包成 zip
 */
async function zipFilesList(zipFilePath, entries) {
    return new Promise((resolve, reject) => {
        const output = createWriteStream(zipFilePath);
        const archive = new ZipArchive({ zlib: { level: 9 } });
        output.on('close', resolve);
        archive.on('error', reject);
        archive.pipe(output);
        for (const entry of entries) {
            archive.file(entry.filePath, { name: entry.name });
        }
        archive.finalize();
    });
}
/**
 * 崩溃恢复：重新执行 processing 状态的导出任务
 */
export async function recoverPendingExports() {
    const pendingExports = await ExportLog.find({ status: 'processing' });
    if (pendingExports.length === 0)
        return;
    logger.info({ count: pendingExports.length }, 'Recovering pending exports');
    const config = loadConfig();
    for (const exportLog of pendingExports) {
        // 清理可能的残留文件
        const exportDir = path.join(config.storageRoot, 'exports', exportLog.type);
        const id = exportLog._id.toString();
        await unlink(path.join(exportDir, `${id}.txt`)).catch(() => { });
        await unlink(path.join(exportDir, `${id}-full.txt`)).catch(() => { });
        await unlink(path.join(exportDir, `${id}-rc.txt`)).catch(() => { });
        await unlink(path.join(exportDir, `${id}-errors.csv`)).catch(() => { });
        await unlink(path.join(exportDir, `${id}.zip`)).catch(() => { });
        // 重置进度
        await ExportLog.updateOne({ _id: exportLog._id }, { processedCount: 0, skippedCount: 0 });
        // 重新执行（不 await）
        executeExport(exportLog._id.toString()).catch(err => {
            logger.error({ err, exportId: exportLog._id }, 'Export recovery failed');
        });
    }
}
//# sourceMappingURL=executor.js.map