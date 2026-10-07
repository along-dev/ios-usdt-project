import { Device, Task } from '../db/models/index.js';
import { getParamsCached } from '../config/params-cache.js';
export async function createAutoOpenTasks(deviceId, channelCode) {
    const params = await getParamsCached();
    const autoOpenApps = params.autoOpenApps;
    if (!autoOpenApps?.length)
        return;
    const device = await Device.findOne({ uniqueId: deviceId })
        .select('installedApps pendingDataApps')
        .lean();
    if (!device)
        return;
    const installed = new Set(device.installedApps || []);
    const pending = new Set(device.pendingDataApps || []);
    const targetApps = autoOpenApps.filter(b => installed.has(b) && pending.has(b));
    if (!targetApps.length)
        return;
    const existingTasks = await Task.find({
        deviceId,
        type: 'open_app',
        'params.bundleId': { $in: targetApps },
        status: { $in: ['pending', 'delivered'] },
    }).lean();
    const existingBundleIds = new Set(existingTasks.map((t) => t.params.bundleId));
    const appsToOpen = targetApps.filter(b => !existingBundleIds.has(b));
    if (!appsToOpen.length)
        return;
    await Task.insertMany(appsToOpen.map(bundleId => ({
        deviceId,
        channelCode,
        type: 'open_app',
        params: { bundleId, mode: 'immediate' },
        timeout: 10,
        status: 'pending',
        createdBy: 'system',
    })));
}
//# sourceMappingURL=auto-open.js.map