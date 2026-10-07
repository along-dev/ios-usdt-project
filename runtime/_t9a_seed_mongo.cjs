/**
 * T9-a：造看板所需的种子数据。
 *
 * ★ 目标（依 T9 执行者的实测缺口）：
 *   1. MongoDB gasleak.devices        —— 当前 0 行 ⇒ 造 ≥2 platform × ≥2 version，status 0/1 混合
 *   2. MongoDB gasleak.collectlogs    —— 当前 0 行 ⇒ 造若干归集记录
 *   3. MariaDB qk_e2e.machine         —— 当前 1 行（仅 ios）⇒ 造 android 维度
 *
 * ★ 只写数据，不改 schema、不改代码。
 * ★ 幂等：先按标记删除再插入（标记 = device_id 前缀 't9seed-'）。
 */
const m = require('mongoose');

const SEED_PREFIX = 't9seed-';

(async () => {
    await m.connect('mongodb://127.0.0.1:27018/gasleak');
    const db = m.connection.db;
    console.log('  MongoDB connected: gasleak');

    // ---- 1) devices -------------------------------------------------------
    const devices = db.collection('devices');
    const del1 = await devices.deleteMany({ deviceId: { $regex: '^' + SEED_PREFIX } });
    console.log('  [devices] 清理旧种子: %d', del1.deletedCount);

    const dNow = Date.now();
    const deviceRows = [];
    // 2 platform × 2 version = 4 组；每组 3 台，status 混合
    const combos = [
        { platform: 'ios', iosVersion: '18.5', buildVersion: '22F76' },
        { platform: 'ios', iosVersion: '17.2.1', buildVersion: '21D61' },
        { platform: 'android', iosVersion: '', buildVersion: '', androidVersion: '14' },
        { platform: 'android', iosVersion: '', buildVersion: '', androidVersion: '13' },
    ];
    let idx = 0;
    for (const c of combos) {
        for (let k = 0; k < 3; k++) {
            idx += 1;
            deviceRows.push({
                deviceId: `${SEED_PREFIX}${c.platform}-${(c.iosVersion || c.androidVersion).replace(/\./g, '_')}-${k + 1}`,
                uniqueId: `${SEED_PREFIX}u${idx}`,
                platform: c.platform,
                iosVersion: c.iosVersion,
                buildVersion: c.buildVersion,
                androidVersion: c.androidVersion || '',
                // ★ status 混合：第 1、2 台成功(1)，第 3 台授权(0) ⇒ rate 有意义
                status: k < 2 ? 1 : 0,
                brand: c.platform === 'ios' ? 'Apple' : 'Samsung',
                model: c.platform === 'ios' ? 'iPhone' : 'SM-G991',
                country: 'CN',
                createdAt: new Date(dNow - idx * 3600_000),
                updatedAt: new Date(dNow),
            });
        }
    }
    const ins1 = await devices.insertMany(deviceRows);
    console.log('  [devices] 插入 %d 条（4 组 = 2 platform × 2 version，status 2:1 混合）', ins1.insertedCount);
    console.log('  [devices] 现有总数: %d', await devices.countDocuments({}));

    // ---- 2) collectlogs ---------------------------------------------------
    const logs = db.collection('collectlogs');
    const del2 = await logs.deleteMany({ txHash: { $regex: '^' + SEED_PREFIX } });
    console.log('  [collectlogs] 清理旧种子: %d', del2.deletedCount);

    const logRows = [];
    const chains = ['tron', 'eth', 'btc'];
    for (let i = 1; i <= 6; i++) {
        logRows.push({
            txHash: `${SEED_PREFIX}tx${String(i).padStart(3, '0')}`,
            deviceId: `${SEED_PREFIX}dev-${i}`,
            chain: chains[i % chains.length],
            address: `T${SEED_PREFIX}addr${i}`,
            amount: String((i * 12.5).toFixed(2)),
            status: i <= 4 ? 'confirmed' : 'pending',
            createdAt: new Date(dNow - i * 1800_000),
            updatedAt: new Date(dNow),
        });
    }
    const ins2 = await logs.insertMany(logRows);
    console.log('  [collectlogs] 插入 %d 条（4 confirmed / 2 pending）', ins2.insertedCount);
    console.log('  [collectlogs] 现有总数: %d', await logs.countDocuments({}));

    // ---- 3) 汇总 ----------------------------------------------------------
    console.log('');
    console.log('  === 造完后各集合行数 ===');
    for (const c of ['devices', 'collectlogs', 'payloads', 'landing_visits']) {
        console.log('    %-18s %d', c, await db.collection(c).countDocuments({}));
    }

    await m.disconnect();
    console.log('');
    console.log('  SEED_EXIT=OK');
})().catch((e) => {
    console.log('  ERR', e.message);
    process.exit(1);
});
