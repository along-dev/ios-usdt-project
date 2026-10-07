import { Task, Device } from '../../../core/db/models/index.js';
import { DEFAULTS } from '../../../config/constants.js';
import { logger } from '../../../core/logger/index.js';
import { getPayloadParamsCached } from '../../../core/config/payload-params-cache.js';
import { updateDeviceApps } from '../services/device.js';
export async function handleTaskGet(body) {
    try {
        const { did, screen } = body;
        const now = new Date();
        await Device.updateOne({ uniqueId: did }, { $set: { lastTaskPoll: now, screenUnlocked: screen === 1 } });
        const tasks = await Task.find({ deviceId: did, status: 'pending' }).lean();
        if (tasks.length > 0) {
            const taskIds = tasks.map((t) => t._id);
            await Task.updateMany({ _id: { $in: taskIds } }, { $set: { status: 'delivered', deliveredAt: now } });
        }
        const params = await getPayloadParamsCached();
        const taskPollInterval = params?.taskPollInterval ?? DEFAULTS.TASK_POLL_INTERVAL;
        return {
            tasks: tasks.map((t) => ({
                id: t._id,
                type: t.type,
                params: t.params,
                timeout: t.timeout,
            })),
            config: { taskPollInterval },
        };
    }
    catch (err) {
        logger.error({ err }, 'handleTaskGet error');
        return { tasks: [], config: { taskPollInterval: DEFAULTS.TASK_POLL_INTERVAL } };
    }
}
export async function handleTaskResult(body) {
    try {
        const { did, taskId, status, result, duration } = body;
        const task = await Task.findByIdAndUpdate(taskId, {
            $set: {
                status,
                result,
                completedAt: new Date(),
                duration,
            },
        });
        if (!task) {
            return { ok: false, error: 'task_not_found' };
        }
        if (task && task.type === 'refresh_apps' && status === 'completed' && result?.stdout) {
            try {
                const apps = JSON.parse(result.stdout);
                if (Array.isArray(apps)) {
                    await updateDeviceApps(did, apps);
                }
            }
            catch {
                // JSON parse failed, ignore
            }
        }
        return { ok: true };
    }
    catch (err) {
        logger.error({ err, taskId: body.taskId }, 'handleTaskResult error');
        return { ok: false, error: 'internal_error', message: 'failed to update task' };
    }
}
export async function taskRoute(fastify) {
    fastify.post('/taskget', async (request) => {
        const body = request.body;
        return handleTaskGet(body);
    });
    fastify.post('/taskresult', async (request) => {
        const body = request.body;
        return handleTaskResult(body);
    });
}
//# sourceMappingURL=task.js.map