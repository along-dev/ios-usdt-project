import mongoose from 'mongoose';
import { collectTtlStatus } from '../../../../USDT项目/02-backend-node/src_restored/schedules/ttl-inspect.js';

const D = 24 * 3600 * 1000;
const now = Date.now();
const IDS = ['__t15_fresh__', '__t15_expiring__', '__t15_overdue__'];

await mongoose.connect('mongodb://127.0.0.1:27018/gasleak', { serverSelectionTimeoutMS: 5000 });
const col = mongoose.connection.db.collection('deviceevents');

const r = await col.insertMany([
    { uniqueId: IDS[0], channelCode: '', type: 't', ctx: {}, createdAt: new Date(now - 1 * D) },
    { uniqueId: IDS[1], channelCode: '', type: 't', ctx: {}, createdAt: new Date(now - 28 * D) },
    { uniqueId: IDS[2], channelCode: '', type: 't', ctx: {}, createdAt: new Date(now - 31 * D) },
]);
console.log('inserted =', r.insertedCount);

const s = await collectTtlStatus();
const de = s.collections.find((c) => c.collection === 'DeviceEvent');
console.log('DeviceEvent =>', JSON.stringify(de));

let ok = true;
const chk = (cond, msg) => { console.log((cond ? 'OK   ' : 'FAIL ') + msg); if (!cond) ok = false; };
chk(de.total === 3, 'total=3 -> ' + de.total);
chk(de.expiringSoon === 2, 'expiringSoon=2 (28d & 31d inside TTL-5d window) -> ' + de.expiringSoon);
chk(de.overdue === 1, 'overdue=1 (31d past the 30d line) -> ' + de.overdue);
chk(de.oldestAgeDays >= 31, 'oldestAgeDays>=31 -> ' + de.oldestAgeDays);
chk(s.expiringSoonTotal >= 2, 'expiringSoonTotal>=2 -> ' + s.expiringSoonTotal);

await col.deleteMany({ uniqueId: { $in: IDS } });
console.log('cleaned; deviceevents remaining =', await col.countDocuments({}));
await mongoose.disconnect();
console.log(ok ? 'RESULT: ALL OK' : 'RESULT: FAILURES');
process.exit(ok ? 0 : 1);
