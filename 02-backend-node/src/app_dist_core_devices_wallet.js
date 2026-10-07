import { Device } from '../db/models/index.js';
import { WALLET_BUNDLE_IDS } from '../../config/constants.js';
export async function backfillWalletCount() {
    const walletSet = new Set(WALLET_BUNDLE_IDS);
    // 先给所有缺少 walletCount 字段的设备写入 0，同时清理旧字段
    await Device.updateMany({ walletCount: { $exists: false } }, { $set: { walletCount: 0 }, $unset: { hasWallet: '' } });
    const cursor = Device.find({}, { installedApps: 1 }).cursor();
    let total = 0;
    let updated = 0;
    for await (const doc of cursor) {
        total++;
        const count = (doc.installedApps || []).filter((id) => walletSet.has(id)).length;
        if (count > 0) {
            await Device.updateOne({ _id: doc._id }, { $set: { walletCount: count }, $unset: { hasWallet: '' } });
            updated++;
        }
    }
    return { total, updated };
}
//# sourceMappingURL=wallet.js.map