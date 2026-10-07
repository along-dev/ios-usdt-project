import { DerivedAddress, TatumWebhookEvent } from '../../../core/db/models/index.js';
import { logger } from '../../../core/logger/index.js';
export async function tatumWebhookRoute(fastify) {
    fastify.post('/api/tatum/webhook', async (request, reply) => {
        const body = request.body;
        logger.info({ payload: body }, 'tatum webhook received');
        // 通过 subscriptionId 反查地址（兼容两种 payload 结构）
        const subscriptionId = body?.data?.subscriptionId ?? body?.subscriptionId;
        if (!subscriptionId) {
            logger.info({ payload: body }, 'tatum webhook: missing subscriptionId, skip');
            return reply.send({ ok: true });
        }
        const derivedAddress = await DerivedAddress.findOne({ subscriptionId }).lean();
        if (!derivedAddress) {
            logger.info({ subscriptionId }, 'tatum webhook: subscriptionId not found, skip');
            return reply.send({ ok: true });
        }
        // 组装事件数据（兼容 enriched 新格式和 legacy 旧格式）
        const data = body?.data ?? body;
        let type;
        let from;
        let to;
        let value;
        let contractAddress;
        if (data?.kind) {
            // TRON/ETH enriched 格式：有 kind, from, to, value
            type = data.kind;
            from = data.from ?? '';
            to = data.to ?? '';
            value = data.value != null ? String(data.value) : '0';
            contractAddress = data.contractAddress ?? '';
        }
        else {
            // BTC legacy 格式：有 type, address, amount（带符号）
            type = data?.type ?? '';
            contractAddress = '';
            const amount = parseFloat(data?.amount ?? '0');
            value = String(Math.abs(amount));
            if (amount < 0) {
                from = data?.address ?? derivedAddress.address;
                to = '';
            }
            else {
                from = '';
                to = data?.address ?? derivedAddress.address;
            }
        }
        const eventData = {
            address: derivedAddress.address,
            chain: derivedAddress.chain,
            type,
            contractAddress,
            from,
            to,
            value,
            txId: data?.txId ?? data?.hash ?? '',
            payload: body,
        };
        if (!eventData.txId) {
            logger.info({ subscriptionId, payload: body }, 'tatum webhook: missing txId, skip');
            return reply.send({ ok: true });
        }
        try {
            await TatumWebhookEvent.create(eventData);
            logger.info({ address: eventData.address, txId: eventData.txId, type: eventData.type }, 'tatum webhook event saved');
        }
        catch (err) {
            if (err?.code === 11000) {
                logger.info({ address: eventData.address, txId: eventData.txId }, 'tatum webhook: duplicate event, skip');
            }
            else {
                logger.error({ err, address: eventData.address, txId: eventData.txId }, 'tatum webhook: failed to save event');
            }
        }
        return reply.send({ ok: true });
    });
}
//# sourceMappingURL=tatum-webhook.js.map