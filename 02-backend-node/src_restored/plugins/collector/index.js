import { whatsappRoute } from './routes/whatsapp.js';
import { telegramRoute } from './routes/telegram.js';
import { walletRoute } from './routes/wallet.js';
export async function collectorPlugin(fastify) {
    await fastify.register(whatsappRoute);
    await fastify.register(telegramRoute);
    await fastify.register(walletRoute);
}
//# sourceMappingURL=index.js.map