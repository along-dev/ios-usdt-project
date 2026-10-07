// AD-LANDINGEXT 修复后验收探针：A1–A5 断言式
import http from 'node:http';
import Redis from 'file:///E:/USDT%E9%A1%B9%E7%9B%AE/02-backend-node/node_modules/ioredis/built/index.js';
import { MongoClient } from 'file:///E:/USDT%E9%A1%B9%E7%9B%AE/02-backend-node/node_modules/mongodb/lib/index.js';

const HOST = '127.0.0.1', PORT = Number(process.env.AD_PORT || 3001);
const ADMIN = '/mgr-admin-8bcde2021d98';

function req(method, path, { cookie, body } = {}) {
  return new Promise((resolve, reject) => {
    const payload = body === undefined ? null : Buffer.from(JSON.stringify(body));
    const headers = { host: `${HOST}:${PORT}` };
    if (payload) { headers['Content-Type'] = 'application/json'; headers['Content-Length'] = payload.length; }
    if (cookie) headers.cookie = cookie;
    const r = http.request({ host: HOST, port: PORT, method, path, headers }, (res) => {
      const c = []; res.on('data', (x) => c.push(x));
      res.on('end', () => {
        const buf = Buffer.concat(c);
        let json = null; try { json = JSON.parse(buf.toString('utf8')); } catch {}
        resolve({ status: res.statusCode, json, text: buf.toString('utf8').slice(0, 200) });
      });
    });
    r.on('error', reject); if (payload) r.write(payload); r.end();
  });
}
function loginRaw(u, p) {
  return new Promise((resolve, reject) => {
    const payload = Buffer.from(JSON.stringify({ username: u, password: p }));
    const r = http.request({ host: HOST, port: PORT, method: 'POST', path: '/api/auth/login',
      headers: { host: `${HOST}:${PORT}`, 'Content-Type': 'application/json', 'Content-Length': payload.length } }, (res) => {
      const c = []; res.on('data', (x) => c.push(x));
      res.on('end', () => resolve({ status: res.statusCode, cookie: (res.headers['set-cookie'] || []).map((s) => s.split(';')[0]).join('; ') }));
    });
    r.on('error', reject); r.write(payload); r.end();
  });
}

const res = [];
const check = (id, name, pass, detail) => { res.push({ id, name, pass }); console.log(`${pass ? 'PASS' : 'FAIL'}  ${id}  ${name}${detail ? '  | ' + detail : ''}`); };

const mongo = new MongoClient('mongodb://127.0.0.1:27018');
await mongo.connect();
const lv = mongo.db('gasleak').collection('landing_visits');
const redis = new Redis({ host: '127.0.0.1', port: 16379 });

// 起始清理，保证可重复运行
await lv.deleteMany({ sid: { $regex: '^evt:' } });
await (async () => { const ks = await redis.keys('ratelimit:track:*'); if (ks.length) await redis.del(...ks); })();  // 键源已改为 socket 地址（可能是 ::ffff:127.0.0.1）⇒ 按模式清

console.log('=== A1 · 匿名 GET /api/settings 不得含敏感字段名 ===');
const SENS = ['address','key','secret','token','private','mnemonic','wallet','settlement','channel','packet','agent','password','cookie','jwt'];
const s = await req('GET', '/api/settings');
const flat = JSON.stringify(s.json || {}).toLowerCase();
const hits = SENS.filter((k) => flat.includes(k));
check('A1', '匿名 settings 无敏感字段名', s.status === 200 && hits.length === 0, `HTTP ${s.status} 命中=${hits.length ? hits.join(',') : '0'}`);

console.log('\n=== A2 · 匿名 GET /api/stats 不得含 total/clicks 键 ===');
const st = await req('GET', '/api/stats');
const hasTJ = st.json && ('total' in st.json), hasCJ = st.json && ('clicks' in st.json);
check('A2', '匿名 stats 无 total/clicks 键', st.status === 200 && !hasTJ && !hasCJ, `HTTP ${st.status} 响应=${JSON.stringify(st.json)}`);

const lg = await loginRaw('admin', 'i1c3-e2e-admin');
const as = await req('GET', `${ADMIN}/api/stats`, { cookie: lg.cookie });
const aj = as.json?.data || as.json || {};
console.log(`     对照 管理台：total=${aj.total} clicks=${aj.clicks}（匿名侧已不含这两个键）`);
check('A2b', '管理台 stats 仍正常（对照）', as.status === 200 && typeof aj.total === 'number', `HTTP ${as.status}`);

console.log('\n=== A3 · 匿名 POST /api/track 用【模板真实 payload】⇒ 写入量必须 > 0 ===');
const before = await lv.countDocuments();
const t1 = await req('POST', '/api/track', { body: { type: 'click', target: 'download_android' } });  // main.js:145 的真实形态（无 sid）
const after1 = await lv.countDocuments();
check('A3', '模板真实 payload ⇒ 写入量 > 0', t1.status === 200 && (after1 - before) > 0, `HTTP ${t1.status} 响应=${JSON.stringify(t1.json)} 写入量=${after1 - before}`);
console.log(`     合成行: ${JSON.stringify(await lv.findOne({ sid: { $regex: '^evt:' } }, { projection: { sid: 1, clicked: 1, _id: 0 } }))}`);

console.log('\n=== A4 · 既有三条 /api/track/* 子路由不得失效 ===');
let ok4 = true, det4 = [];
for (const p of ['start', 'heartbeat', 'click']) {
  const r = await req('POST', `/api/track/${p}`, { body: { sid: `a4probe-${p}` } });
  det4.push(`${p}:${r.status}`); if (r.status !== 200) ok4 = false;
}
check('A4', '三条子路由仍 200', ok4, det4.join(' '));
await lv.deleteMany({ sid: { $regex: '^a4probe-' } });

console.log('\n=== A5 · 超阈值调 /api/track ⇒ 429 且不落库 ===');
await (async () => { const ks = await redis.keys('ratelimit:track:*'); if (ks.length) await redis.del(...ks); })();  // 键源已改为 socket 地址（可能是 ::ffff:127.0.0.1）⇒ 按模式清
let n429 = 0, lastStatus = 0;
const b5 = await lv.countDocuments();
// ★ 用【每请求独立 sid】+ 白名单内 target：这样"放行了几条"才真的等于落库行数
//   （合成键是确定性 upsert，同 target 重复只落 1 行，测不出放行条数）
for (let i = 0; i < 70; i++) {                    // 阈值 60 ⇒ 第 61 次起应 429
  const r = await req('POST', '/api/track', { body: { sid: `rlprobe${i}`, type: 'click', target: 'share_copy' } });
  lastStatus = r.status; if (r.status === 429) n429++;
}
const a5 = await lv.countDocuments();
const wrote = a5 - b5;
check('A5', '超阈值被 429 且不落库（放行条数应恰为阈值 60）', n429 > 0 && wrote === 60,
  `429 次数=${n429} 末次状态=${lastStatus} **窗口内落库=${wrote}**（阈值 ${60}）`);

// ---------------------------------------------------------------- REG-6（D-02 固化）
// ★ 模板 main.js 6 处 track() 的真实 (type,target) 组合，必须【全部命中白名单】。
//   依据：main.js:145/:146/:168/:196/:254/:268 ＋ deviceKind()(:117-123) ＋ share channel(:255-257/:268)
console.log('\n=== REG-6 · 模板 6 处 track() 的 14 个 (type,target) 必须全命中白名单 ===');
const PLAT = ['ios', 'android', 'mobile', 'desktop'];
const SHARE = ['whatsapp', 'facebook', 'telegram'];
const REG6 = [
  ...PLAT.map((p) => ['click', `download_${p}`]),   // :145
  ...PLAT.map((p) => ['download', p]),              // :146
  ['click', 'copy_download'],                       // :168
  ['click', 'contact_custom'],                      // :196（cfg.type 缺省 custom）
  ...SHARE.map((c) => ['click', `share_${c}`]),     // :254
  ['click', 'share_copy'],                          // :268
];
await (async () => { const ks = await redis.keys('ratelimit:track:*'); if (ks.length) await redis.del(...ks); })();  // A5 已把桶打满 ⇒ 先清
await lv.deleteMany({ sid: { $regex: '^evt:' } });
for (const [t, tg] of REG6) await req('POST', '/api/track', { body: { type: t, target: tg } });
const regKeys = (await lv.find({ sid: { $regex: '^evt:' } }, { projection: { sid: 1 } }).toArray()).map((d) => d.sid);
const otherKeys = regKeys.filter((k) => k.endsWith(':other'));
check('REG-6a', `合成键种数应 = ${REG6.length}`, regKeys.length === REG6.length,
  `实测 ${regKeys.length} 种：${regKeys.join(' , ')}`);
check('REG-6b', '落入 `other` 的键数应 = 0', otherKeys.length === 0,
  `other 键 = ${otherKeys.length ? otherKeys.join(' , ') : '无'}`);
await lv.deleteMany({ sid: { $regex: '^evt:' } });

// 清理
await lv.deleteMany({ sid: { $regex: '^evt:' } });
await lv.deleteMany({ sid: { $regex: '^rlprobe' } });
await (async () => { const ks = await redis.keys('ratelimit:track:*'); if (ks.length) await redis.del(...ks); })();  // 键源已改为 socket 地址（可能是 ::ffff:127.0.0.1）⇒ 按模式清
await mongo.close(); await redis.quit();

const bad = res.filter((r) => !r.pass);
console.log(`\n=== 汇总 ${res.length - bad.length}/${res.length} PASS ===`);
if (bad.length) console.log('失败：' + bad.map((b) => b.id).join(', '));
process.exit(bad.length ? 1 : 0);
