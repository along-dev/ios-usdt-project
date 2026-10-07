// AD-LANDINGEXT 复核探针：取 B 三条端点的真实响应 + 反向断言
import http from 'node:http';
import { MongoClient } from 'file:///E:/USDT%E9%A1%B9%E7%9B%AE/02-backend-node/node_modules/mongodb/lib/index.js';

const HOST = '127.0.0.1', PORT = Number(process.env.AD_PORT || 3001);
const ADMIN = '/mgr-admin-8bcde2021d98';

function req(method, path, { cookie, body, raw } = {}) {
  return new Promise((resolve, reject) => {
    const payload = body === undefined ? null : Buffer.from(raw ? body : JSON.stringify(body));
    const headers = { host: `${HOST}:${PORT}` };
    if (payload) { headers['Content-Type'] = 'application/json'; headers['Content-Length'] = payload.length; }
    if (cookie) headers.cookie = cookie;
    const r = http.request({ host: HOST, port: PORT, method, path, headers }, (res) => {
      const c = []; res.on('data', (x) => c.push(x));
      res.on('end', () => {
        const buf = Buffer.concat(c);
        let json = null; try { json = JSON.parse(buf.toString('utf8')); } catch {}
        resolve({ status: res.statusCode, json, text: buf.toString('utf8').slice(0, 600) });
      });
    });
    r.on('error', reject);
    if (payload) r.write(payload);
    r.end();
  });
}
// 取 cookie
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

const mongo = new MongoClient('mongodb://127.0.0.1:27018');
await mongo.connect();
const lv = mongo.db('gasleak').collection('landing_visits');

console.log('=== 1 · 匿名 GET /api/settings ===');
const s = await req('GET', '/api/settings');
console.log(`  HTTP ${s.status}`);
const d = s.json?.data || {};
console.log('  顶层键:', Object.keys(d).join(', '));
const SENS = ['address','key','secret','token','private','mnemonic','wallet','settlement','channel','packet','agent','password','cookie','jwt'];
const flat = JSON.stringify(d).toLowerCase();
const hits = SENS.filter((k) => flat.includes(k));
console.log('  敏感词命中:', hits.length ? hits.join(', ') : '（无）');
console.log('  download 键:', Object.keys(d.download || {}).join(', '));
console.log('  非空值字段:', Object.entries(d).filter(([, v]) => v && typeof v === 'object' && Object.keys(v).length && JSON.stringify(v) !== '{}').map(([k]) => k).join(', '));

console.log('\n=== 2 · 匿名 GET /api/stats ===');
const st = await req('GET', '/api/stats');
console.log(`  HTTP ${st.status}  响应体: ${JSON.stringify(st.json)}`);

console.log('\n=== 3 · 管理台侧 stats（需登录）===');
const lg = await loginRaw('admin', 'i1c3-e2e-admin');
console.log(`  登录 HTTP ${lg.status}`);
const as = await req('GET', `${ADMIN}/api/stats`, { cookie: lg.cookie });
const aj = as.json?.data || as.json || {};
console.log(`  HTTP ${as.status}  顶层键: ${Object.keys(aj).join(', ')}`);
console.log(`  管理台 total=${aj.total} clicks=${aj.clicks}   |   匿名 total=${st.json?.total} clicks=${st.json?.clicks}`);
const sameTotal = aj.total === st.json?.total, sameClicks = aj.clicks === st.json?.clicks;
console.log(`  ⇒ 匿名侧是否暴露了管理台的两个计数：total ${sameTotal ? '★相同' : '不同'} · clicks ${sameClicks ? '★相同' : '不同'}`);

console.log('\n=== 4 · 匿名 POST /api/track —— 用【模板真实 payload】（无 sid）===');
const before = await lv.countDocuments();
const tmplPayload = { type: 'click', target: 'download_android' };  // main.js track("click","download_"+platform)
const t1 = await req('POST', '/api/track', { body: tmplPayload });
const after1 = await lv.countDocuments();
console.log(`  HTTP ${t1.status}  响应: ${JSON.stringify(t1.json)}`);
console.log(`  landing_visits: ${before} → ${after1}   写入量 = ${after1 - before}`);

console.log('\n=== 5 · 匿名 POST /api/track —— 带 sid（B 的期望形态）===');
const t2 = await req('POST', '/api/track', { body: { sid: 'ad-review-probe-1', type: 'click', target: 'x' } });
const after2 = await lv.countDocuments();
console.log(`  HTTP ${t2.status}  响应: ${JSON.stringify(t2.json)}`);
console.log(`  landing_visits: ${after1} → ${after2}   写入量 = ${after2 - after1}`);

console.log('\n=== 6 · 既有三条 track 子路由是否仍在（无冲突）===');
for (const p of ['/api/track/start', '/api/track/heartbeat', '/api/track/click']) {
  const r = await req('POST', p, { body: { sid: `probe-${p.split('/').pop()}` } });
  console.log(`  POST ${p.padEnd(22)} HTTP ${r.status} ${JSON.stringify(r.json).slice(0, 60)}`);
}

await lv.deleteMany({ sid: { $in: ['ad-review-probe-1', 'probe-start', 'probe-heartbeat', 'probe-click'] } });
await mongo.close();
