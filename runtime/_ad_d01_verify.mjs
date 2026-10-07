// D-01 复验（设定后）：① 两条 ERROR 命中=0（含正控）② 不同 XFF 落不同桶 ③ 运行期告警不再触发
import http from 'node:http';
import fs from 'node:fs';
import Redis from 'file:///E:/USDT%E9%A1%B9%E7%9B%AE/02-backend-node/node_modules/ioredis/built/index.js';

const HOST = '127.0.0.1', PORT = Number(process.env.AD_PORT || 3001);
const LOG = 'X:\\_integration\\_fix_work\\_ad3001.out';
const A = '203.0.113.211', B = '203.0.113.212';   // 两个【从未用过】的伪造 IP ⇒ 桶必为新

const post = (xff, body) => new Promise((resolve, reject) => {
  const p = Buffer.from(JSON.stringify(body));
  const r = http.request({ host: HOST, port: PORT, method: 'POST', path: '/api/track',
    headers: { host: `${HOST}:${PORT}`, 'Content-Type': 'application/json', 'Content-Length': p.length, 'X-Forwarded-For': xff } },
    (res) => { const c = []; res.on('data', (x) => c.push(x)); res.on('end', () => resolve(res.statusCode)); });
  r.on('error', reject); r.write(p); r.end();
});
const redis = new Redis({ host: '127.0.0.1', port: 16379 });
const logText = () => { try { return fs.readFileSync(LOG, 'utf8'); } catch { return ''; } };
const count = (re) => (logText().match(re) || []).length;

console.log('=== ③ 先发带 XFF 的请求（触发点）===');
const s1 = await post(A, { type: 'click', target: 'share_copy' });
console.log(`  带 X-Forwarded-For=${A} 的 /api/track ⇒ HTTP ${s1}`);

console.log('\n=== ① 两条 ERROR 的命中数（本实例日志）===');
console.log(`  日志文件            = ${LOG}`);
console.log(`  启动期那条 命中数   = ${count(/LANDING_TRUSTED_PROXIES 为空/g)}    ← 期望 0`);
console.log(`  运行期那条 命中数   = ${count(/收到带 X-Forwarded-For 类头/g)}    ← 期望 0`);
console.log(`  ★ 正控：该日志里 landing-ext 非 ERROR 行 = ${count(/landing-ext \/api\/track 已记录/g)}    ← 必须 ≥1，否则"0 命中"无意义`);

console.log('\n=== ② 不同 XFF ⇒ 不同桶 ===');
const baseA = await redis.get(`ratelimit:track:${A}`), baseB = await redis.get(`ratelimit:track:${B}`);
console.log(`  起始计数： ${A} = ${baseA ?? '(无键)'} ； ${B} = ${baseB ?? '(无键)'}`);
let okA = 0, e429A = 0;
for (let i = 0; i < 61; i++) { const s = await post(A, { type: 'click', target: 'share_copy' }); s === 429 ? e429A++ : okA++; }
const sB = await post(B, { type: 'click', target: 'share_copy' });
const cntA = await redis.get(`ratelimit:track:${A}`), cntB = await redis.get(`ratelimit:track:${B}`);
console.log(`  ${A}：放行 ${okA} 次 / 429 ${e429A} 次（阈值 60）· 桶计数 = ${cntA}`);
console.log(`  ${B}：**同一时刻**再发 1 次 ⇒ HTTP ${sB}（应为 200 ⇒ 说明 B 没被 A 挤占）· 桶计数 = ${cntB}`);
console.log(`  ⇒ 桶键互不相同： ratelimit:track:${A}  vs  ratelimit:track:${B}`);

console.log('\n=== ③ 运行期告警是否被触发（再查一次）===');
console.log(`  运行期那条 命中数 = ${count(/收到带 X-Forwarded-For 类头/g)}    ← 期望 0（白名单已设）`);

console.log('\n=== 汇总 ===');
const pass1 = count(/LANDING_TRUSTED_PROXIES 为空/g) === 0 && count(/收到带 X-Forwarded-For 类头/g) === 0 && count(/landing-ext \/api\/track 已记录/g) >= 1;
const pass2 = e429A > 0 && sB === 200 && cntB !== null && cntA !== cntB;
console.log(`  ① 两条 ERROR=0 且正控≥1 ： ${pass1 ? 'PASS' : 'FAIL'}`);
console.log(`  ② 不同 XFF 落不同桶     ： ${pass2 ? 'PASS' : 'FAIL'}`);

await redis.quit();
