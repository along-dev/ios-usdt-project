// _ad_audit_cache.mjs —— 自查②：landing.js 的 sha256 缓存（key = size:mtimeMs）能否被绕过
// 做法：把 APK 换成【等长但内容不同】的文件并【还原 mtime】⇒ 看端点是否仍按缓存放行。
// 前提：3001 以 LANDING_APK_PATH 指向 _ad_cachetest 启动。
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { MongoClient } from 'file:///E:/USDT%E9%A1%B9%E7%9B%AE/02-backend-node/node_modules/mongodb/lib/index.js';

const HOST = '127.0.0.1';
const PORT = Number(process.env.AD_PORT || 3001);
const DIR = 'X:\\_integration\\_fix_work\\_ad_cachetest';
const APK = path.join(DIR, 'japapp.apk');
const REAL = 'E:\\USDT项目\\02-backend-node\\templates\\apk\\japapp.apk';
const REGISTERED = '30d6701dd6ed010ce842a7d521fed10e4284356270c0214f44aa4fd0792765a5';

function get(p) {
  return new Promise((resolve, reject) => {
    const r = http.request({ host: HOST, port: PORT, method: 'GET', path: p, headers: { host: `${HOST}:${PORT}` } },
      (res) => {
        const chunks = [];
        res.on('data', (c) => chunks.push(c));
        res.on('end', () => resolve({ status: res.statusCode, buf: Buffer.concat(chunks) }));
      });
    r.on('error', reject);
    r.end();
  });
}
const sha = (b) => createHash('sha256').update(b).digest('hex');

// 准备：等长的"替换件"目录
fs.mkdirSync(DIR, { recursive: true });
fs.copyFileSync(REAL, APK);
const st0 = fs.statSync(APK);
console.log(`准备：真实 APK ${st0.size} B，mtimeMs=${st0.mtimeMs}`);

const mongo = new MongoClient('mongodb://127.0.0.1:27018');
await mongo.connect();
const ch = await mongo.db('gasleak').collection('channels').findOne({ groupId: { $ne: '' } });
await mongo.close();
if (!ch) { console.log('无已绑定渠道，无法测'); process.exit(2); }

// 第 1 次：正确文件 ⇒ 应 200 且 sha 命中登记值，并把 size:mtimeMs 写入缓存
const r1 = await get(`/api/apk/download?channel=${ch.code}`);
const s1 = sha(r1.buf);
console.log(`\n[1] 替换前：HTTP ${r1.status} sha=${s1.slice(0, 16)} ${s1 === REGISTERED ? '（= 登记值 ✅）' : '（≠ 登记值 ❌）'}`);

// 替换：等长、不同内容，并把 mtime 还原到与原来【逐位相同】
const evil = Buffer.alloc(st0.size, 0x41);
evil.write('EVIL-REPLACED-PAYLOAD');
fs.writeFileSync(APK, evil);
fs.utimesSync(APK, new Date(st0.atimeMs), new Date(st0.mtimeMs));
const st1 = fs.statSync(APK);

const K = (s) => `${s.ino}:${s.size}:${s.mtimeMs}:${s.ctimeMs}`;
console.log(`\n平台 = ${process.platform}`);
console.log(` 替换前：ino=${st0.ino} size=${st0.size} mtimeMs=${st0.mtimeMs} ctimeMs=${st0.ctimeMs}`);
console.log(` 替换后：ino=${st1.ino} size=${st1.size} mtimeMs=${st1.mtimeMs} ctimeMs=${st1.ctimeMs}`);
console.log(` 等长？ ${st1.size === st0.size ? '✅' : '❌'} · mtime 已还原？ ${st1.mtimeMs === st0.mtimeMs ? '✅' : '❌'}`);
console.log(` 旧键 size:mtimeMs 相同？ ${`${st1.size}:${st1.mtimeMs}` === `${st0.size}:${st0.mtimeMs}` ? '✅（旧实现必然被绕过）' : '❌'}`);
console.log(` 新键 ino:size:mtime:ctime 相同？ ${K(st1) === K(st0) ? '⚠️ 相同 ⇒ 缓存仍会命中' : '✅ 已变 ⇒ 未命中 ⇒ 会重算'}`);

// 第 2 次：同尺寸同 mtime ⇒ 若缓存生效，端点应【跳过校验】并把替换件发出去
const r2 = await get(`/api/apk/download?channel=${ch.code}`);
const s2 = sha(r2.buf);
console.log(`[2] 替换后：HTTP ${r2.status} sha=${s2.slice(0, 16)} 与登记值一致？ ${s2 === REGISTERED ? '是' : '否'}`);

console.log('\n=== 判定（★ 必须带平台口径）===');
if (r2.status === 200 && s2 !== REGISTERED) {
  console.log(`平台 ${process.platform}：⚠️ 本机仍能绕过 ⇒ 键未变、缓存命中、替换件被分发。`);
  console.log('  ⇒ **本机读数如实报**；该修复的保证依赖 Linux 的 ctime 语义（部署形态为 Docker/Linux），');
  console.log('     Windows 上 ctime 语义不同 ⇒ 本机复现不出**不等于**修复失效，但**不得据此判 PASS**。');
} else if (r2.status === 503) {
  console.log(`平台 ${process.platform}：✅ 替换件被拒（503）。`);
  if (process.platform === 'linux') {
    console.log('  原因：键已变（ctime 被内核置位）⇒ 未命中 ⇒ 重算 ⇒ 拒绝 —— 这是**缓存分支**上的判定。');
  } else {
    console.log('  原因：**平台闸生效**（非 Linux ⇒ 缓存关闭 ⇒ 每请求重算）⇒ 拒绝。');
    console.log('  ⚠️ 注意：这条 PASS 只证明「非 Linux 上不会因缓存而放行」，');
    console.log('     **不证明** Linux 缓存分支正确 —— 那要在部署平台复跑（见 L050 §2 部署期验证项 VP-AD-01）。');
  }
} else {
  console.log(`平台 ${process.platform}：HTTP ${r2.status}，需人工判读。`);
}

// 复原目录，避免污染后续测试
fs.copyFileSync(REAL, APK);
console.log('\n（已把 ' + DIR + ' 还原为真实 APK）');
process.exit(0);
