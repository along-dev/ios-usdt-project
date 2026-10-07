import { Device } from '../db/models/index.js';
import { TRACKED_BUNDLE_IDS } from '../../config/constants.js';
const trackedSet = new Set(TRACKED_BUNDLE_IDS);
export async function refreshDeviceAppDataStatus(deviceId) {
    const device = await Device.findOne({ uniqueId: deviceId })
        .select('installedApps wsCount tgCount uploadedDataApps')
        .lean();
    if (!device)
        return;
    const installed = new Set(device.installedApps || []);
    const trackedInstalled = TRACKED_BUNDLE_IDS.filter(b => installed.has(b));
    const uploaded = new Set((device.uploadedDataApps || []).filter((b) => trackedInstalled.includes(b)));
    if ((device.wsCount || 0) > 0)
        uploaded.add('net.whatsapp.WhatsApp');
    if ((device.tgCount || 0) > 0)
        uploaded.add('ph.telegra.Telegraph');
    const pending = trackedInstalled.filter(b => !uploaded.has(b));
    await Device.updateOne({ uniqueId: deviceId }, { $set: { pendingDataApps: pending, uploadedDataApps: [...uploaded] } });
}
export async function markAppDataUploaded(deviceId, bundleId) {
    if (!trackedSet.has(bundleId))
        return;
    await Device.updateOne({ uniqueId: deviceId }, {
        $addToSet: { uploadedDataApps: bundleId },
        $pull: { pendingDataApps: bundleId },
    });
}
//# sourceMappingURL=app-data-status.js.map