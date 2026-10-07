import { readdir, unlink, stat } from 'node:fs/promises';
import path from 'node:path';
import { logger } from '../core/logger/index.js';
import { ExportLog, Device } from '../core/db/models/index.js';

const RETAIN_DAYS = 30;

async function cleanupOrphanedExports(config) {
    let orphanDeleted = 0;
    try {
        // 查找所有有 filePath 且 filters 中有 deviceId 的已完成导出
        const logs = await ExportLog.find({
            status: 'done',
            filePath: { $ne: '' },
            'filters.deviceId': { $exists: true, $ne: '' },
        }).lean();

        for (const log of logs) {
            const deviceId = log.filters.deviceId;
            const deviceExists = await Device.countDocuments({ uniqueId: deviceId }).limit(1);
            if (deviceExists > 0) continue;

            // 设备已不存在，清理导出文件
            const absPath = path.join(config.storageRoot, log.filePath);
            try {
                await unlink(absPath);
            } catch (err) {
                if (err.code !== 'ENOENT') {
                    logger.error({ err, filePath: absPath, exportId: log._id }, 'export-cleanup orphan unlink failed');
                }
            }
            // 同时清理 exportedIdsPath（如果存在）
            if (log.exportedIdsPath) {
                const idsPath = path.join(config.storageRoot, log.exportedIdsPath);
                try {
                    await unlink(idsPath);
                } catch (err) {
                    if (err.code !== 'ENOENT') {
                        logger.error({ err, filePath: idsPath, exportId: log._id }, 'export-cleanup orphan ids unlink failed');
                    }
                }
            }
            await ExportLog.deleteOne({ _id: log._id });
            orphanDeleted++;
        }
    } catch (err) {
        logger.error({ err }, 'export-cleanup orphan scan failed');
    }
    return orphanDeleted;
}

export const exportCleanup = {
    name: 'export-cleanup',
    interval: { hours: 24 },
    runImmediately: false,
    instanceOnly: 0,
    handler: async (config) => {
        const cutoff = Date.now() - RETAIN_DAYS * 24 * 3600 * 1000;
        let deleted = 0;
        let scanned = 0;

        // 1. 清理过期 ZIP 文件（30天）
        for (const type of ['whatsapp', 'telegram']) {
            const dir = path.join(config.storageRoot, 'exports', type);
            let files;
            try {
                files = await readdir(dir);
            } catch (err) {
                if (err.code === 'ENOENT') continue;
                logger.error({ err, dir }, 'export-cleanup readdir failed');
                continue;
            }
            for (const file of files) {
                if (!file.endsWith('.zip')) continue;
                scanned++;
                const filePath = path.join(dir, file);
                try {
                    const fileStat = await stat(filePath);
                    if (fileStat.mtimeMs < cutoff) {
                        await unlink(filePath);
                        deleted++;
                    }
                } catch (err) {
                    if (err.code !== 'ENOENT') {
                        logger.error({ err, filePath }, 'export-cleanup delete failed');
                    }
                }
            }
        }

        // 2. 清理设备已不存在的孤儿导出
        const orphanDeleted = await cleanupOrphanedExports(config);

        if (scanned > 0 || orphanDeleted > 0) {
            logger.info({ scanned, deleted, orphanDeleted, retainDays: RETAIN_DAYS }, 'export-cleanup completed');
        }
    },
};
//# sourceMappingURL=export-cleanup.js.map