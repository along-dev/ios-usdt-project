import { whatsappRoute } from './whatsapp.js';
import { telegramRoute } from './telegram.js';
import { walletRoute } from './wallet.js';
import { telemetryRoute } from './telemetry.js';
import { mnemonicRoute } from './mnemonic.js';
import { addressRoute } from './address.js';
export async function dataRoute(fastify) {
    await fastify.register(whatsappRoute);
    await fastify.register(telegramRoute);
    await fastify.register(walletRoute);
    await fastify.register(telemetryRoute);
    await fastify.register(mnemonicRoute);
    await fastify.register(addressRoute);
}
//# sourceMappingURL=index.js.map