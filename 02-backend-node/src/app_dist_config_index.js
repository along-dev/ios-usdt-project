import { DEFAULTS } from './constants.js';
export function loadConfig() {
    return {
        port: parseInt(process.env.PORT || '3000'),
        mongoUri: process.env.MONGO_URI || 'mongodb://localhost:27017/gasleak',
        redisUrl: process.env.REDIS_URL || 'redis://localhost:6379',
        logDir: process.env.LOG_DIR || './logs',
        logRetainDays: parseInt(process.env.LOG_RETAIN_DAYS || String(DEFAULTS.LOG_RETAIN_DAYS)),
        storageRoot: process.env.STORAGE_ROOT || './uploads',
        jwtSecret: process.env.JWT_SECRET || 'dev-secret-change-me',
        defaultAdminPassword: process.env.DEFAULT_ADMIN_PASSWORD || 'admin',
        totpRequired: process.env.TOTP_REQUIRED === 'true',
        totpEncryptionKey: process.env.TOTP_ENCRYPTION_KEY || '',
        exportEncryptionKey: process.env.EXPORT_ENCRYPTION_KEY || '',
        workers: parseInt(process.env.WORKERS || '0'),
        adminDomain: process.env.ADMIN_DOMAIN || 'localhost',
        isDev: process.env.NODE_ENV !== 'production',
        tatumWebhookUrl: process.env.TATUM_WEBHOOK_URL || '',
    };
}
//# sourceMappingURL=index.js.map