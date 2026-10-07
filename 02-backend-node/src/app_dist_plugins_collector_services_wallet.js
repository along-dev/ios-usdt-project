import { WalletData } from '../../../core/db/models/index.js';
import { getDeviceSourceDomain } from '../../../core/devices/source-domain.js';
const ID_FIELDS = new Set(['a', 'c', 'd', 'd1', 'd2', 'd3', 'v', 'gci']);
export function extractWalletData(body) {
    const data = {};
    for (const [k, v] of Object.entries(body)) {
        if (!ID_FIELDS.has(k)) {
            data[k] = v;
        }
    }
    return data;
}
export async function insertWalletUpload(params) {
    const sourceDomain = await getDeviceSourceDomain(params.deviceId);
    return WalletData.create({
        deviceId: params.deviceId,
        channelCode: params.channelCode,
        sourceDomain,
        walletType: params.walletType,
        api: params.api,
        data: params.data,
        receivedAt: new Date(),
    });
}
//# sourceMappingURL=wallet.js.map