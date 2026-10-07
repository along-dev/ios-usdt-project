import pino from 'pino';
import path from 'node:path';
import { logAls } from './context.js';
const isDev = process.env.NODE_ENV !== 'production';
const logDir = process.env.LOG_DIR || './logs';
const instanceId = process.env.NODE_APP_INSTANCE || '0';
const transportPath = path.join(import.meta.dirname, 'transport.js');
const devTransportPath = path.join(import.meta.dirname, 'transport-dev.js');
export const logger = pino({
    level: isDev ? 'debug' : 'info',
    timestamp() {
        const now = new Date(Date.now() + 8 * 3600_000);
        return `,"time":"${now.toISOString().replace('T', ' ').replace('Z', '').slice(0, 23)}"`;
    },
    mixin() {
        const store = logAls.getStore();
        return store ? { ...store } : { stream: 'system' };
    },
    transport: isDev
        ? { target: devTransportPath }
        : {
            target: transportPath,
            options: { logDir, instanceId },
        },
});
export { logAls } from './context.js';
//# sourceMappingURL=index.js.map