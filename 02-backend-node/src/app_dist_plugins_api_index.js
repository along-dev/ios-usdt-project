import { logger } from '../../core/logger/index.js';
import { authMiddleware } from './middleware/auth.js';
import { authRoute } from './routes/auth.js';
import { usersRoute } from './routes/users.js';
import { channelsRoute } from './routes/channels.js';
import { devicesRoute } from './routes/devices.js';
import { dataRoute } from './routes/data/index.js';
import { dashboardRoute } from './routes/dashboard.js';
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
    await fastify.register(channelStatsRoute);
    await fastify.register(payloadsRoute);
    await fastify.register(paramsRoute);
    await fastify.register(payloadParamsRoute);
    await fastify.register(tasksRoute);
    await fastify.register(applicationRoute);
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