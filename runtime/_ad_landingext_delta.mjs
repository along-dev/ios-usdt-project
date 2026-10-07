// AD-01/02 修复后的 delta 验证 + 强制回归（模板 6 处 track 的真实 (type,target) 必须不被归 other）
import http from 'node:http';
import Redis from 'file:///E:/USDT%E9%A1%B9%E7%9B%AE/02-backend-node/node_modules/ioredis/built/index.js';
import { MongoClient } from 'file:///E:/USDT%E9%A1%B9%E7%9B%AE/02-backend-node/node_modules/mongodb/lib/index.js';

const HOST = '127.0.0.1', PORT = Number(process.env.AD_PORT || 3001);
const R = [];
const chk = (id, name, pass, d) => { R.push({ id, pass }); console.log(`${pass ? 'PASS' : 'FAIL'}  ${id}  ${name}${d ? '\n      ' + d : ''}`); };

function post(path, body, headers = {}) {
  return new Promise((resolve, reject) => {
    const p = Buffer.from(JSON.stringify(body));
    const r = http.request({ host: HOST, port: PORT, method: 'POST', path,
      headers: { host: `${HOST}:${PORT}`, 'Content-Type': 'application/json', 'Content-Length': p.length, ...headers } },
      (res) => { const c = []; res.on('data', (x) => c.push(x)); res.on('end', () => { let j = null;
        try { j = JSON.parse(Buffer.concat(c).toString('utf8')); } catch {} resolve({ status: res.statusCode, json: j }); }); });
    r.on('error', reject); r.write(p); r.end();
  });
}
const mongo = new MongoClient('mongodb://127.0.0.1:27018'); await mongo.connect();
const lv = mongo.db('gasleak').collection('landing_visits');
const redis = new Redis({ host: '127.0.0.1', port: 16379 });
const clearRl = async () => { const ks = await redis.keys('ratelimit:track:*'); if (ks.length) await redis.del(...ks); };
await lv.deleteMany({ sid: { $regex: '^evt:' } }); await clearRl();

// ---------------------------------------------------------------- 强制回归（AD-01）
console.log('=== 强制回归：模板 main.js 6 处 track() 的真实 (type,target) 必须【不被归 other】 ===');
const PLAT = ['ios', 'android', 'mobile', 'desktop'];          // main.js:117-123 deviceKind()
const SHARE = ['whatsapp', 'facebook', 'telegram'];            // main.js:255-257 + :268
const CASES = [
  ...PLAT.map((p) => ['click', `download_${p}`, ':145']),
  ...PLAT.map((p) => ['download', p, ':146']),
  ['click', 'copy_download', ':168'],
  ['click', 'contact_custom', ':196'],                          // cfg.type 缺省 custom
  ...SHARE.map((c) => ['click', `share_${c}`, ':254']),
  ['click', 'share_copy', ':268'],
];
const bad = [];
for (const [t, tg, src] of CASES) {
  const r = await post('/api/track', { type: t, target: tg });
  const doc = await lv.findOne({ sid: `evt:${t}:${tg}` });
  const okRec = r.status === 200 && doc && !String(doc.sid).includes(':other');
  if (!okRec) bad.push(`${src} ${t}/${tg} ⇒ HTTP ${r.status} sid=${doc ? doc.sid : '（未落库）'}`);
}
await lv.deleteMany({ sid: { $regex: '^evt:' } });
chk('REG-6', `模板 6 处调用共 ${CASES.length} 个 (type,target) 全在白名单内`, bad.length === 0,
  bad.length ? bad.join(' ; ') : `全部命中白名单，无一条落入 other（用例覆盖 :145/:146/:168/:196/:254/:268）`);

// ---------------------------------------------------------------- AD-01：基数有界
// 设计：type 用【合法值】(click)，只让 target 伪造 ⇒ 若无白名单，会生成 N 个不同键；
//       有白名单 ⇒ 全部塌进 evt:click:other（1 个）。阈值 60 会截断部分请求，但 60 > 24 已足以说明。
console.log('\n=== AD-01：任意 target 连发 N 次 ⇒ 合成键【种数不随 N 增长】 ===');
const N = 150;
for (let i = 0; i < N; i++) await post('/api/track', { type: 'click', target: `evil_${i}` });
const all = await lv.find({ sid: { $regex: '^evt:' } }, { projection: { sid: 1 } }).toArray();
const keys = new Set(all.map((d) => d.sid));
const leaked = [...keys].filter((k) => k.includes('evil_'));
chk('AD-01', `连发 ${N} 次伪造 target ⇒ 合成键种数 ≤ 24 且【无一个 evil_ 键】`,
  keys.size <= 24 && leaked.length === 0,
  `实发 ${N} 次（阈值 60 截断部分）· 落库合成键 ${all.length} 行 · **种数 = ${keys.size}** · 含 evil_ 的键 = ${leaked.length}\n      键集合 = ${[...keys].join(' , ')}`);
await lv.deleteMany({ sid: { $regex: '^evt:' } }); await clearRl();

// ---------------------------------------------------------------- AD-02：伪造 IP 不能突破限频
console.log('\n=== AD-02：每次换一个伪造 X-Real-IP / cf-connecting-ip ⇒ 仍必须被限频 ===');
await clearRl();
let n429 = 0;
for (let i = 0; i < 80; i++) {
  const r = await post('/api/track', { type: 'click', target: 'share_copy' },
    { 'X-Real-IP': `10.99.${i % 250}.${i}`, 'cf-connecting-ip': `10.88.${i % 250}.${i}` });
  if (r.status === 429) n429++;
}
chk('AD-02', '伪造 IP 轮换 80 次 ⇒ 仍出现 429（桶未被伪造重置）', n429 > 0,
  `80 次请求中 429 = **${n429}**（阈值 60）⇒ 伪造 X-Real-IP / cf-connecting-ip 不再换来新配额`);
await lv.deleteMany({ sid: { $regex: '^evt:' } }); await clearRl();

// ---------------------------------------------------------------- 复跑 A1–A5
console.log('\n=== 复跑既有 A1–A5（回归） ===');
const { spawnSync } = await import('node:child_process');
const r = spawnSync('E:/CTF/runtime/node/node.exe', ['X:/_integration/_fix_work/_ad_landingext_verify.mjs'],
  { env: { ...process.env, AD_PORT: String(PORT) }, encoding: 'utf8' });
const tail = (r.stdout || '').split('\n').slice(-4).join('\n');
const passCount = ((r.stdout || '').match(/^PASS  /gm) || []).length;
chk('A1-5', `verify 内 PASS 条数应为 8（实测 ${passCount}）`, passCount === 8 && (r.stdout || '').includes('8/8 PASS'),
  `spawn status=${r.status} · stdout 尾：\n      ${(r.stdout || '').split('\n').slice(-3).join('\n      ')}`);

await mongo.close(); await redis.quit();
console.log(`\n=== delta 汇总：${R.filter((x) => x.pass).length}/${R.length} PASS ===`);
process.exit(R.every((x) => x.pass) ? 0 : 1);
