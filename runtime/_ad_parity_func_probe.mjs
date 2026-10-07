// AD-PARITY-FUNC 探针：对 B 报告 §2.3 的 19 条端点做【功能级】核对（不以 200 为通过）
// 目标实例：3001 隔离实例。共享 3000 不碰。
import http from 'node:http';
import { MongoClient } from 'file:///E:/USDT%E9%A1%B9%E7%9B%AE/02-backend-node/node_modules/mongodb/lib/index.js';

const HOST = '127.0.0.1', PORT = Number(process.env.AD_PORT || 3001);
const A = '/mgr-admin-8bcde2021d98';
const rows = [];
const rec = (n, ep, verdict, detail) => { rows.push({ n, ep, verdict, detail }); console.log(`[${verdict}] ${String(n).padStart(2)} ${ep}\n      ${detail}`); };

function req(method, path, { cookie, body, headers = {} } = {}) {
  return new Promise((resolve, reject) => {
    const payload = body === undefined ? null
      : (body instanceof Buffer ? body : Buffer.from(JSON.stringify(body)));
    const h = { host: `${HOST}:${PORT}`, ...headers };
    if (payload) { if (!h['Content-Type']) h['Content-Type'] = 'application/json'; h['Content-Length'] = payload.length; }
    if (cookie) h.cookie = cookie;
    const r = http.request({ host: HOST, port: PORT, method, path, headers: h }, (res) => {
      const c = []; res.on('data', (x) => c.push(x));
      res.on('end', () => {
        const buf = Buffer.concat(c);
        let json = null; try { json = JSON.parse(buf.toString('utf8')); } catch {}
        resolve({ status: res.statusCode, json, buf, setCookie: (res.headers['set-cookie'] || []).map((s) => s.split(';')[0]).join('; ') });
      });
    });
    r.on('error', reject); if (payload) r.write(payload); r.end();
  });
}
const login = async (u, p) => (await req('POST', `${A}/login`, { body: { username: u, password: p } })).setCookie;
const has = (o, ks) => ks.every((k) => o && Object.prototype.hasOwnProperty.call(o, k));

const mongo = new MongoClient('mongodb://127.0.0.1:27018');
await mongo.connect();
const db = mongo.db('gasleak');
const lv = db.collection('landing_visits');

const ck = await login('admin', 'i1c3-e2e-admin');
console.log(`管理员会话：${ck ? '已取得' : '未取得'}\n`);

// ---------------------------------------------------------------- 1 login
{
  const r = await req('POST', `${A}/login`, { body: { username: 'admin', password: 'i1c3-e2e-admin' } });
  rec(1, 'POST {ADMIN}/login', r.status === 200 && !!r.setCookie ? 'PASS(功能)' : 'FAIL',
    `HTTP ${r.status}，Set-Cookie ${r.setCookie ? '有' : '无'}；★ 响应形态为 JSON（参考侧登录是表单页）⇒ **形态未与参考对照，标 SKIP**`);
}
// ---------------------------------------------------------------- 2 logout
{
  const tmp = await login('admin', 'i1c3-e2e-admin');
  const r = await req('GET', `${A}/logout`, { cookie: tmp });
  const after = await req('GET', `${A}/api/stats`, { cookie: tmp });
  rec(2, 'GET {ADMIN}/logout', after.status === 401 ? 'PASS(功能)' : 'FAIL',
    `logout HTTP ${r.status}；**登出后同一 cookie 访问 ${A}/api/stats ⇒ HTTP ${after.status}**（401 = 会话确已失效）`);
}
// ---------------------------------------------------------------- 6 apk-url
{
  const r = await req('GET', `${A}/api/apk-url`, { cookie: ck });
  rec(6, 'GET {ADMIN}/api/apk-url', has(r.json, ['url']) ? 'PASS(字段)' : 'FAIL',
    `HTTP ${r.status} 响应键=${JSON.stringify(Object.keys(r.json || {}))}（参考 :765 读 d.url）`);
}
// ---------------------------------------------------------------- 7 download-mode
{
  const g = await req('GET', `${A}/api/download-mode`, { cookie: ck });
  const before = g.json?.mode;
  const all = [];
  for (const m of ['link', 'upload', 'telegram']) {
    const p = await req('POST', `${A}/api/download-mode`, { cookie: ck, body: { mode: m } });
    all.push(`${m}:${p.status}/${JSON.stringify(p.json)}`);
  }
  await req('POST', `${A}/api/download-mode`, { cookie: ck, body: { mode: before } });  // 还原
  const back = (await req('GET', `${A}/api/download-mode`, { cookie: ck })).json?.mode;
  rec(7, 'GET/POST {ADMIN}/api/download-mode', has(g.json, ['mode']) ? 'PASS(字段)' : 'FAIL',
    `GET ${JSON.stringify(g.json)}；三种取值 POST ⇒ ${all.join(' | ')}；已还原=${back === before}`);
}
// ---------------------------------------------------------------- 8 template
{
  const g = await req('GET', `${A}/api/template`, { cookie: ck });
  rec(8, 'GET {ADMIN}/api/template', has(g.json, ['template']) ? 'PASS(字段)' : 'FAIL',
    `HTTP ${g.status} 响应=${JSON.stringify(g.json)}（参考 :1040 读 d.template）`);
}
// ---------------------------------------------------------------- 9 theme
{
  const g = await req('GET', `${A}/api/theme`, { cookie: ck });
  rec(9, 'GET {ADMIN}/api/theme', has(g.json, ['theme']) ? 'PASS(字段)' : 'FAIL',
    `HTTP ${g.status} 响应=${JSON.stringify(g.json)}（参考 :908 读 d.theme）`);
}
// ---------------------------------------------------------------- 10 pixel
{
  const g = await req('GET', `${A}/api/pixel`, { cookie: ck });
  rec(10, 'GET {ADMIN}/api/pixel', has(g.json, ['pixel_ids']) ? 'PASS(字段)' : 'FAIL',
    `HTTP ${g.status} 响应=${JSON.stringify(g.json)}（参考 :955 读 d.pixel_ids）`);
}
// ---------------------------------------------------------------- 11 admin stats
{
  const r = await req('GET', `${A}/api/stats`, { cookie: ck });
  const d = r.json?.data || r.json || {};
  const REF11 = ['total', 'today', 'clicks', 'unique_ips', 'avg_dwell_ms', 'top_countries', 'top_devices'];
  const miss = REF11.filter((k) => !(k in d));
  rec(11, 'GET {ADMIN}/api/stats', miss.length === 0 ? 'PASS(字段)' : 'FAIL',
    `参考 :723 消费 ${REF11.length} 个键；**缺失=${miss.length ? miss.join(',') : '无'}**；实测键=${JSON.stringify(Object.keys(d))}`);
}
// ---------------------------------------------------------------- 12 visits
{
  const r = await req('GET', `${A}/api/visits?page=1&per=5`, { cookie: ck });
  const d = r.json?.data || r.json || {};
  const REF12 = ['started_at', 'ip', 'country', 'city', 'device', 'os', 'browser', 'lang', 'dwell_ms', 'clicked', 'referer', 'ua'];
  const row0 = (d.rows || [])[0] || {};
  const miss = REF12.filter((k) => !(k in row0));
  rec(12, 'GET {ADMIN}/api/visits', has(d, ['total', 'rows']) && (d.rows || []).length > 0 && miss.length === 0 ? 'PASS(字段)' : 'FAIL',
    `HTTP ${r.status}；total=${d.total}；rows=${(d.rows || []).length}；**行字段数=${Object.keys(row0).length}**；参考消费 12 个键，**缺失=${miss.length ? miss.join(',') : '无'}**`);
}

// ---------------------------------------------------------------- 4 apk/list
{
  const r = await req('GET', `${A}/api/apk/list`, { cookie: ck });
  const f0 = (r.json?.files || [])[0] || {};
  const REF4 = ['id', 'original_name', 'size', 'tg_file_id', 'uploaded_at'];
  const miss = REF4.filter((k) => !(k in f0));
  rec(4, 'GET {ADMIN}/api/apk/list', has(r.json, ['files']) && miss.length === 0 ? 'PASS(字段)' : 'FAIL',
    `HTTP ${r.status}；files=${(r.json?.files || []).length}；首个元素字段=${Object.keys(f0).length}；参考消费 ${REF4.join('/')}，**缺失=${miss.length ? miss.join(',') : '无'}**`);
}

// ---------------------------------------------------------------- 3+5 upload/delete（自足：传一个假的、再删掉）
{
  const boundary = '----ADPARITY' + Date.now();
  const body = Buffer.concat([
    Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="apk"; filename="ad-parity-dummy.apk"\r\nContent-Type: application/octet-stream\r\n\r\n`),
    Buffer.from('NOT-A-REAL-APK-' + Date.now()),
    Buffer.from(`\r\n--${boundary}--\r\n`),
  ]);
  const up = await req('POST', `${A}/api/apk/upload`, { cookie: ck, body,
    headers: { 'Content-Type': `multipart/form-data; boundary=${boundary}` } });
  const REF3 = ['filename', 'size', 'tg_ok'];
  const missU = REF3.filter((k) => !(k in (up.json || {})));
  rec(3, 'POST {ADMIN}/api/apk/upload', up.status === 200 && missU.length === 0 ? 'PASS(字段)' : 'FAIL',
    `HTTP ${up.status} 响应=${JSON.stringify(up.json)}；参考消费 ${REF3.join('/')}，**缺失=${missU.length ? missU.join(',') : '无'}**`);

  const list = await req('GET', `${A}/api/apk/list`, { cookie: ck });
  const mine = (list.json?.files || []).find((f) => String(f.original_name || '').includes('ad-parity-dummy'));
  if (!mine) rec(5, 'POST {ADMIN}/api/apk/delete', 'SKIP', '上一步未产生可删对象 ⇒ 成功路径无法测（**不删任何真实 APK**）');
  else {
    const del = await req('POST', `${A}/api/apk/delete`, { cookie: ck, body: { id: mine.id } });
    const after = await req('GET', `${A}/api/apk/list`, { cookie: ck });
    const gone = !(after.json?.files || []).some((f) => String(f.original_name || '').includes('ad-parity-dummy'));
    rec(5, 'POST {ADMIN}/api/apk/delete', del.status === 200 && gone ? 'PASS(功能)' : 'FAIL',
      `HTTP ${del.status} 响应=${JSON.stringify(del.json)}；删除后清单里该件**已消失=${gone}**（只删自建 dummy）`);
  }
}

// ---------------------------------------------------------------- 13 visits/clear（快照 + 还原）
{
  const snap = await lv.find({}).toArray();
  const beforeN = snap.length;
  const cl = await req('POST', `${A}/api/visits/clear`, { cookie: ck });
  const afterN = await lv.countDocuments();
  await lv.insertMany(snap);                       // ★ 还原共享数据
  const restoredN = await lv.countDocuments();
  rec(13, 'POST {ADMIN}/api/visits/clear', cl.status === 200 && afterN === 0 && restoredN === beforeN ? 'PASS(功能)' : 'FAIL',
    `HTTP ${cl.status}；清空前 ${beforeN} → 清空后 **${afterN}**（==0 ⇒ 确实生效）→ **已还原至 ${restoredN}**（快照回填）`);
}

// ---------------------------------------------------------------- 14 /api/template（匿名）
{
  const r = await req('GET', '/api/template');
  rec(14, 'GET /api/template（匿名）', has(r.json, ['template']) ? 'PASS(字段)' : 'FAIL', `HTTP ${r.status} 响应=${JSON.stringify(r.json)}`);
}
// ---------------------------------------------------------------- 15 /api/pixel-config（匿名）
{
  const r = await req('GET', '/api/pixel-config');
  rec(15, 'GET /api/pixel-config（匿名）', has(r.json, ['pixel_ids']) ? 'PASS(字段)' : 'FAIL', `HTTP ${r.status} 响应=${JSON.stringify(r.json)}`);
}
// ---------------------------------------------------------------- 16-18 track/*
{
  for (const [n, p] of [[16, 'start'], [17, 'heartbeat'], [18, 'click']]) {
    const sid = `parity-${p}-${Date.now()}`;
    const r1 = await req('POST', `/api/track/${p}`, { body: { sid, dwell: 1234 } });
    const r2 = await req('POST', `/api/track/${p}`, { body: { sid, dwell: 1234 } });   // 幂等：同 sid 再打一次
    const n1 = await lv.countDocuments({ sid });
    const doc = await lv.findOne({ sid }, { projection: { sid: 1, started: 1, dwell: 1, clicked: 1, _id: 0 } });
    await lv.deleteMany({ sid });
    rec(n, `POST /api/track/${p}`, r1.status === 200 && n1 === 1 ? 'PASS(行为)' : 'FAIL',
      `两次同 sid ⇒ HTTP ${r1.status}/${r2.status}；**落库行数=${n1}**（幂等应为 1）；行=${JSON.stringify(doc)}`);
  }
}
// ---------------------------------------------------------------- 19 /api/apk/download
{
  const ch = await db.collection('channels').findOne({ groupId: { $ne: '' } });
  const r = await req('GET', `/api/apk/download?channel=${ch?.code || ''}`);
  rec(19, 'GET /api/apk/download', r.status === 200 && r.buf.length > 1000000 ? 'PASS(功能)' : 'FAIL',
    `HTTP ${r.status} 字节=${r.buf.length}（渠道 ${ch?.code?.slice(0, 12) || '无'}）`);
}
// ------------------------------------------------- 新增三条（缺口 1/2/3 修复后的端点）
{
  const s = await req('GET', '/api/settings');
  rec(20, 'GET /api/settings（缺口1）', !!s.json?.data ? 'PASS(字段)' : 'FAIL', `HTTP ${s.status} data 嵌套=${!!s.json?.data}`);

  const st = await req('GET', '/api/stats');
  const adminSt = await req('GET', `${A}/api/stats`, { cookie: ck });
  const ad = adminSt.json?.data || adminSt.json || {};
  const leaked = ['total', 'clicks'].filter((k) => k in (st.json || {}));
  rec(21, 'GET /api/stats（缺口2·匿名）', leaked.length === 0 ? 'PASS' : 'FAIL',
    `匿名=${JSON.stringify(st.json)}；管理台 total=${ad.total} clicks=${ad.clicks}；**同名量泄漏=${leaked.length ? leaked.join(',') : '无'}**`);

  const t = await req('POST', '/api/track', { body: { type: 'click', target: 'download_android' } });
  const n = await lv.countDocuments({ sid: 'evt:click:download_android' });
  await lv.deleteMany({ sid: { $regex: '^evt:' } });
  rec(22, 'POST /api/track（缺口3）', t.status === 200 && n === 1 ? 'PASS(行为)' : 'FAIL',
    `HTTP ${t.status} 响应=${JSON.stringify(t.json)}；合成行落库=${n}`);
}

await mongo.close();
console.log('\n=== 汇总 ===');
const cnt = rows.reduce((a, r) => { a[r.verdict.split('(')[0]] = (a[r.verdict.split('(')[0]] || 0) + 1; return a; }, {});
console.log(JSON.stringify(cnt));
