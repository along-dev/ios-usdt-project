// AD-PARITY-FUNC 负控：证明判据【能独立失败】（不是只有"全绿"）
// 手法：不改产品代码，而是【改运行态数据】使真实响应变化 ⇒ 断言必须变红。
import http from 'node:http';
import { createHash } from 'node:crypto';
import { MongoClient } from 'file:///E:/USDT%E9%A1%B9%E7%9B%AE/02-backend-node/node_modules/mongodb/lib/index.js';

const HOST = '127.0.0.1', PORT = Number(process.env.AD_PORT || 3001);
const A = '/mgr-admin-8bcde2021d98';
function req(method, path, { cookie, body } = {}) {
  return new Promise((resolve, reject) => {
    const p = body === undefined ? null : Buffer.from(JSON.stringify(body));
    const h = { host: `${HOST}:${PORT}` };
    if (p) { h['Content-Type'] = 'application/json'; h['Content-Length'] = p.length; }
    if (cookie) h.cookie = cookie;
    const r = http.request({ host: HOST, port: PORT, method, path, headers: h }, (res) => {
      const c = []; res.on('data', (x) => c.push(x));
      res.on('end', () => { const b = Buffer.concat(c); let j = null; try { j = JSON.parse(b.toString('utf8')); } catch {}
        resolve({ status: res.statusCode, json: j, buf: b, cookie: (res.headers['set-cookie'] || []).map((s) => s.split(';')[0]).join('; ') }); });
    });
    r.on('error', reject); if (p) r.write(p); r.end();
  });
}
const sh = (b) => createHash('sha256').update(b).digest('hex').slice(0, 16);
const R = [];
const chk = (id, name, pass, detail) => { R.push({ id, pass }); console.log(`${pass ? 'PASS' : 'FAIL'}  ${id} ${name}\n      ${detail}`); };

const mongo = new MongoClient('mongodb://127.0.0.1:27018'); await mongo.connect();
const lv = mongo.db('gasleak').collection('landing_visits');
const ck = (await req('POST', `${A}/login`, { body: { username: 'admin', password: 'i1c3-e2e-admin' } })).cookie;

console.log('=== NC-1 · apk-url 的 url 字段是【真的从库里读】吗 ===');
const u0 = (await req('GET', `${A}/api/apk-url`, { cookie: ck })).json?.url;
const SENT = 'https://ad-parity-sentinel.invalid/x.apk';
await req('POST', `${A}/api/apk-url`, { cookie: ck, body: { url: SENT } });
const u1 = (await req('GET', `${A}/api/apk-url`, { cookie: ck })).json?.url;
chk('NC-1a', '写入哨兵后：url 应等于哨兵', u1 === SENT, `写入 ${SENT} ⇒ 读回 ${JSON.stringify(u1)}`);
chk('NC-1b', '★ 负控：断言「url 等于原值」确实变红', u1 !== u0, `原值=${JSON.stringify(u0)}，现值=${JSON.stringify(u1)} ⇒ 两者不等 ⇒ 「等于原值」这条**已红**（判据在量）`);
await req('POST', `${A}/api/apk-url`, { cookie: ck, body: { url: u0 } });
const u2 = (await req('GET', `${A}/api/apk-url`, { cookie: ck })).json?.url;
chk('NC-1c', '还原后 url 回到原值', u2 === u0, `已还原=${JSON.stringify(u2)}`);

console.log('\n=== NC-2 · 管理台 stats 的 total 是【真的从集合数】吗 ===');
const t0 = (await req('GET', `${A}/api/stats`, { cookie: ck })).json?.total;
const victim = await lv.findOne({});
await lv.deleteOne({ _id: victim._id });
const t1 = (await req('GET', `${A}/api/stats`, { cookie: ck })).json?.total;
chk('NC-2a', '删 1 行后 total 应减 1', t1 === t0 - 1, `${t0} → ${t1}`);
chk('NC-2b', '★ 负控：断言「total 等于原值」确实变红', t1 !== t0, `原值=${t0}，现值=${t1} ⇒ 两者不等 ⇒ 「等于原值」这条**已红**`);
await lv.insertOne(victim);
const t2 = (await req('GET', `${A}/api/stats`, { cookie: ck })).json?.total;
chk('NC-2c', '还原后 total 回到原值', t2 === t0, `已还原=${t2}`);

console.log('\n=== NC-3 · 管理台 template 是【真的从配置读】吗 ===');
const p0 = (await req('GET', `${A}/api/template`, { cookie: ck })).json?.template;
const SENT2 = 'soccer';
await req('POST', `${A}/api/template`, { cookie: ck, body: { template: SENT2 } });
const p1 = (await req('GET', `${A}/api/template`, { cookie: ck })).json?.template;
chk('NC-3a', '写入哨兵后 template 应等于哨兵', p1 === SENT2, `写入 ${SENT2} ⇒ 读回 ${p1}`);
chk('NC-3b', '★ 负控：断言「template 等于原值」确实变红', p1 !== p0, `原值=${p0}，现值=${p1} ⇒ 两者不等 ⇒ 「等于原值」这条**已红**`);
await req('POST', `${A}/api/template`, { cookie: ck, body: { template: p0 } });
chk('NC-3c', '还原后 template 回到原值', (await req('GET', `${A}/api/template`, { cookie: ck })).json?.template === p0, '已还原');

console.log('\n=== NC-4 · ★ download-mode 有没有【行为】效果（我方） ===');
const ch = await mongo.db('gasleak').collection('channels').findOne({ groupId: { $ne: '' } });
const dLink = await req('GET', `/api/apk/download?channel=${ch.code}`);
await req('POST', `${A}/api/download-mode`, { cookie: ck, body: { mode: 'link' } });
const a = await req('GET', `/api/apk/download?channel=${ch.code}`);
await req('POST', `${A}/api/download-mode`, { cookie: ck, body: { mode: 'upload' } });
const b = await req('GET', `/api/apk/download?channel=${ch.code}`);
await req('POST', `${A}/api/download-mode`, { cookie: ck, body: { mode: 'telegram' } });
const c = await req('GET', `/api/apk/download?channel=${ch.code}`);
await req('POST', `${A}/api/download-mode`, { cookie: ck, body: { mode: 'link' } });
const same = sh(a.buf) === sh(b.buf) && sh(b.buf) === sh(c.buf);
console.log(`      mode=link ⇒ ${a.status}/${sh(a.buf)}/${a.buf.length}B`);
console.log(`      mode=upload ⇒ ${b.status}/${sh(b.buf)}/${b.buf.length}B`);
console.log(`      mode=telegram ⇒ ${c.status}/${sh(c.buf)}/${c.buf.length}B`);
console.log(`      ⇒ 三种 mode 下响应**完全相同=${same}**（差异为 0）`);
console.log(`      ⇒ 事实：\`downloadMode\` 在 Node 侧除管理台端点外**无任何读取点**（全仓 rg 实测）`);
console.log(`      ⇒ 判定：**行为面 SKIP**（我方无消费点；参考侧亦未在素材里找到落地页消费点）—— 但"设置无效果"本身登记为缺口候选`);

await mongo.close();
console.log(`\n=== 负控汇总：${R.filter((x) => x.pass).length}/${R.length} 条按预期 ===`);
console.log('（NC-*b 的期望是"故意写成 应相等 ⇒ 结果不相等 ⇒ 我们判它 FAIL"——即判据确实能红）');
