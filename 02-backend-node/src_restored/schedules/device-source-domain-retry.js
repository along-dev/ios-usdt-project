import { runDeviceSourceDomainRetryBatch } from '../core/devices/source-domain-retry.js';
let isRunning = false;
export const deviceSourceDomainRetry = {
    name: 'device-source-domain-retry',
    interval: { seconds: 5 },
    runImmediately: false,
    instanceOnly: 1,
    handler: async () => {
        if (isRunning)
            return;
        isRunning = true;
        try {
            await runDeviceSourceDomainRetryBatch(100);
        }
        finally {
            isRunning = false;
        }
    },
};
//# sourceMappingURL=device-source-domain-retry.js.map