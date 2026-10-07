import { Task } from '../core/db/models/index.js';
import { DEFAULTS } from '../config/constants.js';
import { logger } from '../core/logger/index.js';
export const taskTimeoutTask = {
    name: 'task-timeout',
    interval: { hours: 1 },
    runImmediately: false,
    handler: async () => {
        try {
            const now = new Date();
            const threshold = new Date(now.getTime() - DEFAULTS.TASK_TIMEOUT_THRESHOLD_MS);
            const deliveredResult = await Task.updateMany({ status: 'delivered', deliveredAt: { $lt: threshold } }, { $set: { status: 'timeout', result: { error: 'no_response' }, completedAt: now } });
            const pendingResult = await Task.updateMany({ status: 'pending', createdAt: { $lt: threshold } }, { $set: { status: 'timeout', result: { error: 'not_delivered' }, completedAt: now } });
            const total = (deliveredResult.modifiedCount || 0) + (pendingResult.modifiedCount || 0);
            if (total > 0) {
                logger.info({ delivered: deliveredResult.modifiedCount, pending: pendingResult.modifiedCount }, 'task-timeout: marked tasks as timeout');
            }
        }
        catch (err) {
            logger.error({ err }, 'task-timeout: handler error');
        }
    },
};
//# sourceMappingURL=task-timeout.js.map