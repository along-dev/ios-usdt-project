import { readdir, unlink } from 'node:fs/promises';
import path from 'node:path';
import { logger } from '../core/logger/index.js';
const LOG_PATTERN = /^w\d+-\w+-(\d{4}-\d{2}-\d{2})\.log$/;
export const logCleanup = {
    name: 'log-cleanup',
    interval: { hours: 1 },
    runImmediately: true,
    instanceOnly: 0,
    handler: async (config) => {
        const start = Date.now();
        const cutoff = Date.now() - config.logRetainDays * 24 * 3600 * 1000;
        const deletedFiles = [];
        let scanned = 0;
        try {
            const files = await readdir(config.logDir);
            for (const file of files) {
                const match = LOG_PATTERN.exec(file);
                if (!match)
                    continue;
                scanned++;
                const fileDate = new Date(match[1] + 'T00:00:00').getTime();
                if (fileDate < cutoff) {
                    const filePath = path.join(config.logDir, file);
                    await unlink(filePath);
                    deletedFiles.push(filePath);
                }
            }
            logger.info({ scanned, deleted: deletedFiles.length, deletedFiles, retainDays: config.logRetainDays, duration: Date.now() - start }, 'log-cleanup completed');
        }
        catch (err) {
            if (err.code === 'ENOENT') {
                logger.info({ logDir: config.logDir }, 'Log directory not found, skipping cleanup');
            }
            else {
                logger.error({ err, logDir: config.logDir }, 'Log cleanup failed');
            }
        }
    },
};
//# sourceMappingURL=log-cleanup.js.map